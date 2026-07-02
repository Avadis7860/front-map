"""usage — index INVERSE de consommation du design-system (imports TSX, best-effort pur-Python).

Répond « qui consomme quelle primitive / quel token ? » — l'inverse des extracteurs de catalogue
(`primitives`/`tokens` listent CE QUI EXISTE ; `usage` liste QUI S'EN SERT). Ce n'est **PAS** un graphe
d'imports général (ça, c'est `code-map`) : on ne cherche QUE les consommateurs du **vocabulaire déjà connu
de front-map** — les primitives déclarées par le barrel et les tokens déclarés par le CSS. Trois signaux :
- **primitive-usage** (déterministe) : `import { Button } from '@/components/ui'` → consomme Button ;
- **token-usage** (best-effort) : occurrence LITTÉRALE d'un nom de token connu (`var(--color-accent-500)`) —
  ne capture PAS la forme utilitaire Tailwind (`text-accent-500`), assumé (pas d'AST CSS-in-JS) ;
- **lien route** (enrichissement) : si le fichier est le composant d'une route, on rattache son `full_path`.

Frontière (jumeau de code-map, inchangée) : re-parse les imports EN INTERNE et ÉTROITEMENT (regex, comme le
barrel de `primitives`), NE dépend PAS de code-map, NE modélise PAS tous les imports. **Pur-Python** → marche
même sans tree-sitter (les noms de primitives viennent de `parse_barrel`, regex) ; seul le lien route se
dégrade à vide quand `routes` est vide (tree-sitter absent).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from frontmap.config import Config

ENGINE = "imports-usage-v1"

# `import { A, B } from '…'` (multiligne via re.S) — capture (type-only?, spécificateurs, source).
_IMPORT = re.compile(r"import\s+(type\s+)?\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]", re.S)
_SUFFIXES = (".tsx", ".ts")


def _resolve_module(source: str, importer_rel: str, web_root: str) -> str | None:
    """Chemin rel (sans extension) d'un import LOCAL. `@/x`→`<web_root>/x` ; `./x`/`../x` relatif au fichier
    importateur. None pour un import de package nu (`react`, `@tanstack/…`) — pas une source locale."""
    s = source.strip("'\"`")
    if s.startswith("@/"):
        rel = f"{web_root}/{s[2:]}"
    elif s.startswith(("./", "../")):
        rel = os.path.normpath(str(Path(importer_rel).parent / s)).replace(os.sep, "/")
    else:
        return None
    return rel.rstrip("/")


def _named_imports(text: str) -> list[tuple[str, list[str]]]:
    """(source, [noms de VALEUR importés]) pour chaque `import { … } from '…'` (type-only ignoré)."""
    out: list[tuple[str, list[str]]] = []
    for m in _IMPORT.finditer(text):
        if m.group(1):  # `import type { … }` → tout l'import est type-only
            continue
        names: list[str] = []
        for spec in m.group(2).split(","):
            spec = spec.strip()
            if not spec or spec.startswith("type "):  # `{ type X, Button }` → spécificateur type inline
                continue
            names.append(spec.split(" as ")[0].strip())
        out.append((m.group(3), names))
    return out


def _barrel_targets(cfg: Config) -> set[str]:
    """Formes rel (sans extension) qu'un import du barrel peut résoudre : le dossier + son `index`."""
    d = Path(cfg.primitives_barrel).parent.as_posix()   # ex. web/src/components/ui
    return {d, f"{d}/index"}


def _primitive_imports(text: str, importer_rel: str, cfg: Config, primitive_names: set[str]) -> list[str]:
    """Primitives connues importées DEPUIS le barrel dans ce fichier (triées)."""
    targets = _barrel_targets(cfg)
    found: set[str] = set()
    for source, names in _named_imports(text):
        resolved = _resolve_module(source, importer_rel, cfg.web_root)
        if resolved is None or resolved not in targets:
            continue
        found.update(n for n in names if n in primitive_names)
    return sorted(found)


def _token_refs(text: str, token_names: set[str]) -> list[str]:
    """Tokens connus référencés LITTÉRALEMENT (frontière de mot pour éviter les sur-préfixes)."""
    found: list[str] = []
    for name in token_names:
        if re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", text):
            found.append(name)
    return sorted(found)


def consumer_files(root: Path, cfg: Config) -> list[str]:
    """Fichiers `.tsx`/`.ts` sous `web_root` susceptibles de consommer le DS — hors primitives (`ui/`),
    router, tests et `.d.ts`. Triés (déterminisme + base du hash de fraîcheur)."""
    root = Path(root)
    web = root / cfg.web_root
    if not web.is_dir():
        return []
    ui_dir = Path(cfg.primitives_barrel).parent.as_posix() + "/"
    out: list[str] = []
    for p in web.rglob("*"):
        if p.suffix not in _SUFFIXES or not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel == cfg.router_file or rel.startswith(ui_dir):
            continue
        if p.name.endswith(".d.ts") or ".test." in p.name or ".spec." in p.name:
            continue
        if "/test/" in f"/{rel}" or "/__tests__/" in f"/{rel}":
            continue
        out.append(rel)
    return sorted(out)


def _route_by_file(root: Path, cfg: Config, routes_rows: list[dict]) -> dict[str, str]:
    """{fichier_consommateur → full_path} en résolvant les imports de composants du router."""
    if not routes_rows:
        return {}
    root = Path(root)
    rpath = root / cfg.router_file
    if not rpath.is_file():
        return {}
    name_to_file: dict[str, str] = {}
    for source, names in _named_imports(rpath.read_text(encoding="utf-8")):
        resolved = _resolve_module(source, cfg.router_file, cfg.web_root)
        if resolved is None:
            continue
        target = next((f"{resolved}{sfx}" for sfx in _SUFFIXES
                       if (root / f"{resolved}{sfx}").is_file()), None)
        if target is None:
            continue
        for n in names:
            name_to_file[n] = target
    out: dict[str, str] = {}
    for r in routes_rows:
        comp = (r.get("component") or "").strip()
        f = name_to_file.get(comp)
        if f and r.get("full_path"):
            out[f] = r["full_path"]
    return out


def extract_usage(root: Path, cfg: Config, primitive_names: set[str], token_names: set[str],
                  routes_rows: list[dict]) -> list[dict]:
    """Consommation du DS par fichier. Un fichier sans AUCUNE primitive NI token connu est omis (ce n'est
    pas un consommateur du design-system). `route` = None si le fichier n'est pas un composant de route."""
    root = Path(root)
    route_by_file = _route_by_file(root, cfg, routes_rows)
    rows: list[dict] = []
    for rel in consumer_files(root, cfg):
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        prims = _primitive_imports(text, rel, cfg, primitive_names)
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
