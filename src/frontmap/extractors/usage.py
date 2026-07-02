"""usage — index INVERSE de consommation du design-system (imports TSX, best-effort pur-Python).

Répond « qui consomme quelle primitive / quel token ? » — l'inverse des extracteurs de catalogue
(`primitives`/`tokens` listent CE QUI EXISTE ; `usage` liste QUI S'EN SERT). Ce n'est **PAS** un graphe
d'imports général (ça, c'est `code-map`) : on ne cherche QUE les consommateurs du **vocabulaire déjà connu
de front-map**. Trois signaux :
- **primitive-usage** (déterministe) : délégué à l'adaptateur primitives (`consumed_primitives`), qui sait
  comment SA convention importe une primitive (nommé depuis un barrel, défaut depuis un fichier) ;
- **token-usage** (best-effort) : occurrence LITTÉRALE d'un nom de token connu (`var(--color-accent-500)`) —
  ne capture PAS la forme utilitaire Tailwind, assumé (pas d'AST CSS-in-JS) ;
- **lien route** (enrichissement) : si le fichier est le composant d'une route, on rattache son `full_path`.

Frontière (jumeau de code-map, inchangée) : re-parse les imports EN INTERNE et ÉTROITEMENT (regex, module
`imports`), NE dépend PAS de code-map. **Pur-Python** → marche sans tree-sitter (les noms de primitives
viennent de l'adaptateur, regex/filesystem) ; seul le lien route se dégrade à vide quand `routes` est vide.
"""
from __future__ import annotations

import re
from pathlib import Path

from frontmap import imports
from frontmap.adapters.base import PrimitivesAdapter, RouteRow
from frontmap.config import Config

ENGINE = "imports-usage-v1"
_SUFFIXES = (".tsx", ".ts")


def _token_refs(text: str, token_names: set[str]) -> list[str]:
    """Tokens connus référencés LITTÉRALEMENT (frontière de mot pour éviter les sur-préfixes)."""
    found: list[str] = []
    for name in token_names:
        if re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", text):
            found.append(name)
    return sorted(found)


def consumer_files(root: Path, cfg: Config, ui_dir: str) -> list[str]:
    """Fichiers `.tsx`/`.ts` sous `web_root` susceptibles de consommer le DS — hors primitives (`ui_dir`),
    router, tests et `.d.ts`. Triés (déterminisme + base du hash de fraîcheur)."""
    root = Path(root)
    web = root / cfg.web_root
    if not web.is_dir():
        return []
    ui_prefix = ui_dir.rstrip("/") + "/"
    out: list[str] = []
    for p in web.rglob("*"):
        if p.suffix not in _SUFFIXES or not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel == cfg.router_file or rel.startswith(ui_prefix):
            continue
        if p.name.endswith(".d.ts") or ".test." in p.name or ".spec." in p.name:
            continue
        if "/test/" in f"/{rel}" or "/__tests__/" in f"/{rel}":
            continue
        out.append(rel)
    return sorted(out)


def _route_by_file(root: Path, cfg: Config, routes_rows: list[RouteRow]) -> dict[str, str]:
    """{fichier_consommateur → full_path} via les imports de composants du router (nommés + défaut)."""
    if not routes_rows:
        return {}
    root = Path(root)
    rpath = root / cfg.router_file
    if not rpath.is_file():
        return {}
    text = rpath.read_text(encoding="utf-8", errors="replace")
    name_to_file: dict[str, str] = {}
    pairs: list[tuple[str, str]] = [(src, n) for src, names in imports.named_imports(text) for n in names]
    pairs += imports.default_imports(text)
    for source, local in pairs:
        resolved = imports.resolve_module(source, cfg.router_file, cfg.web_root, cfg.import_alias)
        if resolved is None:
            continue
        target = next((f"{resolved}{sfx}" for sfx in _SUFFIXES
                       if (root / f"{resolved}{sfx}").is_file()), None)
        if target is not None:
            name_to_file[local] = target
    out: dict[str, str] = {}
    for r in routes_rows:
        comp = (r.get("component") or "").strip()
        f = name_to_file.get(comp)
        if f and r.get("full_path"):
            out[f] = r["full_path"]
    return out


def extract_usage(root: Path, cfg: Config, prim: PrimitivesAdapter, primitive_names: set[str],
                  token_names: set[str], routes_rows: list[RouteRow]) -> list[dict]:
    """Consommation du DS par fichier. Un fichier sans AUCUNE primitive NI token connu est omis. La
    détection des primitives est déléguée à l'adaptateur (`prim.consumed_primitives`) → générique par
    convention. `route` = None si le fichier n'est pas un composant de route."""
    root = Path(root)
    route_by_file = _route_by_file(root, cfg, routes_rows)
    rows: list[dict] = []
    for rel in consumer_files(root, cfg, prim.ui_dir(root, cfg)):
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        prims = prim.consumed_primitives(text, rel, cfg, primitive_names)
        toks = _token_refs(text, token_names)
        if not prims and not toks:
            continue
        rows.append({
            "consumer": rel,
            "kind": "page" if "/pages/" in f"/{rel}" else "component",
            "primitives": prims,
            "tokens": toks,
            "route": route_by_file.get(rel),
        })
    rows.sort(key=lambda x: x["consumer"])
    return rows
