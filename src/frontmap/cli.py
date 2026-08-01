"""cli — porte d'entrée unifiée `frontmap` (jumeau front de `codemap`).

Une commande, des sous-commandes, un `--root`, un `.frontmap.toml`. `build` écrit les index ; les autres
verbes lisent. Sortie JSON stable (chaque verbe renvoie un dict + `engine`) → consommable par un agent.

Sous-commandes :
  build                    (re)construit les 4 index (tokens/primitives/routes/usage), incrémental par hash
  tokens [--group G]       design tokens (filtre optionnel par groupe)
  primitives               catalogue des primitives (résumé)
  primitive <name>         détail d'une primitive (props, variantes, defaults)
  routes                   arbre des routes
  where <intention>        « quelle primitive / quel token pour X ? » (ranking lexical borné)
  usage <name>             « qui consomme cette primitive / ce token ? » (index inversé)
  consumers <file>         ce qu'un écran consomme (primitives + tokens + route)
  detect                   conventions (router / primitives) auto-détectées du repo
  check                    cohérence + fraîcheur de l'index
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from frontmap import __version__
from frontmap.config import INDEX_DIRNAME, Config
from frontmap.core import roots

_borrow_warned = False


def _sentinel() -> str:
    """Marqueur « un build a réellement tourné » : le manifest — la même constante que `check` interroge
    déjà, pas une sentinelle neuve. Import **paresseux** (`frontmap.build` tire les adaptateurs et
    tree-sitter : `--help` n'a pas à les charger) et **sans duplication**, donc rien qui puisse dériver."""
    from frontmap.build import MANIFEST_NAME
    return MANIFEST_NAME


def _warn_borrow(main_root: Path) -> None:
    """Annonce l'emprunt d'index sur **stderr** — le JSON de stdout n'est pas touché (un consommateur qui
    parse la sortie ne doit pas voir apparaître un champ pour une information d'ergonomie CLI ; c'est aussi
    ce qu'a tranché code-map, dont l'enveloppe est un contrat versionné). Invariant maison respecté : jamais
    de cap silencieux, toute borne se signale.

    Émis **une seule fois par invocation** de `main()` (qui remet le drapeau à zéro) : `main()` re-résout
    pour sa garde `needs_index`, le message sortirait sinon en double."""
    global _borrow_warned
    if _borrow_warned:
        return
    _borrow_warned = True
    print(f"⚠ index emprunté au répertoire principal ({main_root})", file=sys.stderr)
    print("  → ne voit pas le code de cette worktree ; `frontmap build` pour l'à-jour", file=sys.stderr)


_STALE_CAP = 5      # fichiers nommés par catégorie ; le reste est COMPTÉ, jamais tu (invariant maison)


def _fmt_files(paths: list[str]) -> str:
    """Liste bornée : au plus `_STALE_CAP` chemins, puis le compte du reste. Un cap qui ne s'annonce pas est
    un mensonge par omission — même invariant que `check`, qui ne rend jamais un vert partiel."""
    rest = len(paths) - _STALE_CAP
    head = ", ".join(paths[:_STALE_CAP])
    return f"{head} … +{rest} autre(s)" if rest > 0 else head


def _warn_stale(fresh: dict) -> None:
    """Annonce la péremption de l'index sur **stderr** — même contrat que `_warn_borrow` : le JSON de stdout
    n'est pas touché.

    POURQUOI AUX VERBES DE LECTURE et pas seulement dans `check` : `check` savait déjà tout, mais il n'est
    prescrit nulle part dans la règle anti-archéologie — les agents lisent par `where`/`primitives`/`tokens`,
    qui servaient leur catalogue avec l'autorité d'un index et **0 octet sur stderr**.

    LE SPÉCIMEN QUI A MOTIVÉ CE SIGNAL (mesuré le 2026-08-01 sur le cockpit, index gelé au 07-25 alors que
    `web/` avait bougé le 07-31) : `FileDrop.tsx` existait, exporté par le barrel et consommé par un écran ;
    `frontmap primitives` en listait **16** sans lui, et `frontmap where "zone de dépôt de fichier"` rendait
    `{"results": []}` — rc 0, stderr vide. Une session qui applique « ne réinvente pas un primitive existant,
    `frontmap where` d'abord » recevait un **vide confiant** et réécrivait le composant. C'est la forme la
    plus coûteuse du faux-vert : elle supprime le doute.

    Porte sur l'**état de l'index**, pas sur la réponse rendue : un fichier jamais indexé n'apparaît dans
    aucun hit — restreindre l'avertissement aux fichiers cités serait muet là où le silence est le plus
    dangereux, c'est-à-dire exactement sur le spécimen ci-dessus.
    """
    if "files" not in fresh or fresh.get("ok"):     # index absent (déjà dit ailleurs) ou frais → silence
        return
    cats = (("∅", "jamais indexé(s)", fresh["unindexed"]),
            ("≠", "modifié(s) depuis le build", fresh["drifted"]),
            ("–", "disparu(s) du disque", fresh["removed"]))
    resume = [f"{len(v)} {label}" for _, label, v in cats if v]
    if fresh["ts_changed"]:
        resume.append("dispo tree-sitter changée")
    if fresh["conventions_changed"]:
        resume.append("convention (router/primitives) changée")
    print(f"⚠ index périmé — {', '.join(resume) or 'cause non détaillée'}", file=sys.stderr)
    for sigil, _, v in cats:
        if v:
            print(f"  {sigil} {_fmt_files(v)}", file=sys.stderr)
    print("  → `frontmap build` pour l'à-jour", file=sys.stderr)


def _resolve(root_opt: str | None, *, borrow: bool = False) -> tuple[Path, Path, Config]:
    """Résout (racine, dossier d'index, config) pour toute sous-commande.

    `borrow=True` (verbes de **lecture** seulement) : dans une worktree liée SANS index propre — les index
    dérivés ne sont pas versionnés, `git worktree add` ne les emporte donc pas — on lit celui du répertoire
    de travail principal plutôt que de laisser l'appelant fouiller le front à l'aveugle. L'emprunt s'annonce
    sur stderr (fraîcheur : l'index du principal ignore le code de la worktree).

    Deux exclusions **délibérées**, toutes deux par le même critère « que fait ce verbe de `index_dir` ? » :

    - `build` **écrit** — emprunter reviendrait à écrire l'index de la feature dans le répertoire principal
      (corruption silencieuse de celui de `dev`). Le critère est l'écriture, jamais le nom du verbe.
    - `check` **diagnostique l'index local** — répondre avec celui du principal transformerait « tu n'as pas
      d'index ici » en verdict vert sur l'index d'un autre. Il porte déjà son `ok:false` honnête.
    """
    root = roots.project_root(root_opt)
    index_dir = root / INDEX_DIRNAME
    if borrow and not (index_dir / _sentinel()).is_file():
        main_root = roots.main_worktree_root(root)
        if main_root is not None and (main_root / INDEX_DIRNAME / _sentinel()).is_file():
            _warn_borrow(main_root)
            index_dir = main_root / INDEX_DIRNAME
    return root, index_dir, Config.load(root)


def _emit(data: dict) -> int:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def _cmd_build(a: argparse.Namespace) -> int:
    from frontmap import build as build_mod

    # PAS d'emprunt : `build` ÉCRIT dans `index_dir`. Emprunter y écrirait l'index de cette worktree dans
    # le répertoire principal — la corruption exacte que la garde vise.
    root, index_dir, cfg = _resolve(a.root)
    return _emit(build_mod.build(root, index_dir, cfg, force=a.force))


def _cmd_tokens(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root, borrow=True)
    return _emit(query.tokens(index_dir, a.group))


def _cmd_primitives(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root, borrow=True)
    return _emit(query.primitives(index_dir))


def _cmd_primitive(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root, borrow=True)
    return _emit(query.primitive(index_dir, a.name))


def _cmd_routes(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root, borrow=True)
    return _emit(query.routes(index_dir))


def _cmd_where(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root, borrow=True)
    return _emit(query.where(index_dir, a.intent, top_k=a.top_k))


def _cmd_usage(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root, borrow=True)
    return _emit(query.usage(index_dir, a.name))


def _cmd_consumers(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root, borrow=True)
    return _emit(query.consumers(index_dir, a.file))


def _cmd_detect(a: argparse.Namespace) -> int:
    from frontmap import adapters
    root, _, cfg = _resolve(a.root)
    return _emit({**adapters.detect(root, cfg), "engine": "frontmap-v1"})


def _cmd_check(a: argparse.Namespace) -> int:
    from frontmap import query

    # PAS d'emprunt (ni de garde `needs_index`) : `check` est le diagnostic de l'index LOCAL. Répondre avec
    # celui du principal changerait de sujet — « tu n'as pas d'index ici » deviendrait un verdict vert sur
    # l'index d'un autre. Il porte déjà son `ok:false` « index absent » honnête.
    root, index_dir, cfg = _resolve(a.root)
    res = query.check(index_dir, root, cfg)
    _emit(res)
    return 0 if res.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="frontmap", description="index design-system déterministe (front)")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="racine du repo (défaut : repère .frontmap.toml/.git depuis le cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", parents=[common], help="(re)construit les index")
    b.add_argument("--force", action="store_true", help="ignore le skip d'idempotence")
    b.set_defaults(func=_cmd_build)

    # `needs_index=True` marque les verbes de LECTURE : ils exigent un index déjà bâti. `main()` les garde
    # (message actionnable si l'index manque) — vs `build`, qui le bâtit, et `detect`/`check`, qui n'en
    # dépendent pas (`detect` lit les sources ; `check` diagnostique l'absence lui-même).
    t = sub.add_parser("tokens", parents=[common], help="design tokens")
    t.add_argument("--group", help="filtre par groupe (accent|status|surface|radius|shadow|motion|z|…)")
    t.set_defaults(func=_cmd_tokens, needs_index=True)

    ps = sub.add_parser("primitives", parents=[common], help="catalogue des primitives")
    ps.set_defaults(func=_cmd_primitives, needs_index=True)

    p = sub.add_parser("primitive", parents=[common], help="détail d'une primitive")
    p.add_argument("name")
    p.set_defaults(func=_cmd_primitive, needs_index=True)

    r = sub.add_parser("routes", parents=[common], help="arbre des routes")
    r.set_defaults(func=_cmd_routes, needs_index=True)

    w = sub.add_parser("where", parents=[common], help="quelle primitive/token pour une intention")
    w.add_argument("intent")
    w.add_argument("--top-k", type=int, default=5)
    w.set_defaults(func=_cmd_where, needs_index=True)

    u = sub.add_parser("usage", parents=[common], help="qui consomme cette primitive/ce token")
    u.add_argument("name")
    u.set_defaults(func=_cmd_usage, needs_index=True)

    cn = sub.add_parser("consumers", parents=[common], help="ce qu'un écran consomme")
    cn.add_argument("file")
    cn.set_defaults(func=_cmd_consumers, needs_index=True)

    dt = sub.add_parser("detect", parents=[common], help="conventions auto-détectées (router / primitives)")
    dt.set_defaults(func=_cmd_detect)

    c = sub.add_parser("check", parents=[common], help="cohérence + fraîcheur de l'index")
    c.set_defaults(func=_cmd_check)

    return ap


def main(argv=None) -> int:
    global _borrow_warned
    _borrow_warned = False  # état par INVOCATION (et non par processus) : `main()` rappelé en test/in-process
    ap = build_parser()
    a = ap.parse_args(argv)
    # Garde index-absent pour les verbes de lecture : sans elle, `tokens`/`primitives`/`routes`/… renvoient
    # un vide TROMPEUR (`read_jsonl` rend `[]` sur fichier absent → `{"tokens": [], "count": 0}`, rc 0 :
    # impossible de distinguer « pas de token » de « pas d'index »). On dégrade proprement : même forme que
    # `check`, message actionnable, rc inchangé. Le manifest est le marqueur « un build a tourné ».
    if getattr(a, "needs_index", False):
        root, index_dir, cfg = _resolve(a.root, borrow=True)
        if not (index_dir / _sentinel()).is_file():
            from frontmap.query import ENGINE
            return _emit({"ok": False, "reason": "index absent — lance `frontmap build`", "engine": ENGINE})
        # Fraîcheur : un index périmé se servait en SILENCE (2026-08-01 — le cockpit servait un catalogue
        # de 16 primitives amputé de `FileDrop`, livré 6 jours plus tôt). Point d'appel UNIQUE, ici :
        # l'index est déjà résolu et les 7 verbes de lecture y passent tous.
        # Index EMPRUNTÉ ⇒ on se tait : hacher le front de cette worktree contre le manifest du répertoire
        # principal rendrait tout le diff de la feature « périmé », par-dessus un avertissement qui dit
        # déjà exactement cela.
        if not _borrow_warned:
            from frontmap import query
            _warn_stale(query.freshness(index_dir, root, cfg))
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
