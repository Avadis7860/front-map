"""cli — porte d'entrée unifiée `frontmap` (jumeau front de `codemap`).

Une commande, des sous-commandes, un `--root`, un `.frontmap.toml`. `build` écrit les index ; les autres
verbes lisent. Sortie JSON stable (chaque verbe renvoie un dict + `engine`) → consommable par un agent.

Sous-commandes :
  build                    (re)construit les 3 index (tokens + primitives + routes), incrémental par hash
  tokens [--group G]       design tokens (filtre optionnel par groupe)
  primitives               catalogue des primitives (résumé)
  primitive <name>         détail d'une primitive (props, variantes, defaults)
  routes                   arbre des routes
  where <intention>        « quelle primitive / quel token pour X ? » (ranking lexical borné)
  usage <name>             « qui consomme cette primitive / ce token ? » (index inversé)
  consumers <file>         ce qu'un écran consomme (primitives + tokens + route)
  check                    cohérence + fraîcheur de l'index
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from frontmap import __version__
from frontmap.config import INDEX_DIRNAME, Config
from frontmap.core import roots


def _resolve(root_opt: str | None) -> tuple[Path, Path, Config]:
    """Résout (racine, dossier d'index, config) pour toute sous-commande."""
    root = roots.project_root(root_opt)
    return root, root / INDEX_DIRNAME, Config.load(root)


def _emit(data: dict) -> int:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def _cmd_build(a: argparse.Namespace) -> int:
    from frontmap import build as build_mod
    root, index_dir, cfg = _resolve(a.root)
    return _emit(build_mod.build(root, index_dir, cfg, force=a.force))


def _cmd_tokens(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root)
    return _emit(query.tokens(index_dir, a.group))


def _cmd_primitives(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root)
    return _emit(query.primitives(index_dir))


def _cmd_primitive(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root)
    return _emit(query.primitive(index_dir, a.name))


def _cmd_routes(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root)
    return _emit(query.routes(index_dir))


def _cmd_where(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root)
    return _emit(query.where(index_dir, a.intent, top_k=a.top_k))


def _cmd_usage(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root)
    return _emit(query.usage(index_dir, a.name))


def _cmd_consumers(a: argparse.Namespace) -> int:
    from frontmap import query
    _, index_dir, _ = _resolve(a.root)
    return _emit(query.consumers(index_dir, a.file))


def _cmd_check(a: argparse.Namespace) -> int:
    from frontmap import query
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

    t = sub.add_parser("tokens", parents=[common], help="design tokens")
    t.add_argument("--group", help="filtre par groupe (accent|status|surface|radius|shadow|motion|z|…)")
    t.set_defaults(func=_cmd_tokens)

    ps = sub.add_parser("primitives", parents=[common], help="catalogue des primitives")
    ps.set_defaults(func=_cmd_primitives)

    p = sub.add_parser("primitive", parents=[common], help="détail d'une primitive")
    p.add_argument("name")
    p.set_defaults(func=_cmd_primitive)

    r = sub.add_parser("routes", parents=[common], help="arbre des routes")
    r.set_defaults(func=_cmd_routes)

    w = sub.add_parser("where", parents=[common], help="quelle primitive/token pour une intention")
    w.add_argument("intent")
    w.add_argument("--top-k", type=int, default=5)
    w.set_defaults(func=_cmd_where)

    u = sub.add_parser("usage", parents=[common], help="qui consomme cette primitive/ce token")
    u.add_argument("name")
    u.set_defaults(func=_cmd_usage)

    cn = sub.add_parser("consumers", parents=[common], help="ce qu'un écran consomme")
    cn.add_argument("file")
    cn.set_defaults(func=_cmd_consumers)

    c = sub.add_parser("check", parents=[common], help="cohérence + fraîcheur de l'index")
    c.set_defaults(func=_cmd_check)

    return ap


def main(argv=None) -> int:
    ap = build_parser()
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
