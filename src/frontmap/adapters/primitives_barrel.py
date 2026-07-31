"""primitives_barrel — convention « barrel » : `components/ui/index.ts` ré-exporte les primitives.

Autorité = le barrel (`export { Button } from './Button'`). Consommation = import NOMMÉ depuis le dossier
du barrel (`import { Button } from '@/components/ui'`). C'est la convention du nouveau cockpit (TanStack).
`primitive_names` (regex, sans tree-sitter) est le contrat pivot ; le détail props/variants passe par
`tsx_component` (best-effort tree-sitter).
"""
from __future__ import annotations

import re
from pathlib import Path

from frontmap import imports, tsparse
from frontmap.adapters import tsx_component
from frontmap.adapters.base import PrimitiveRow
from frontmap.config import Config

# `export { Button, type ButtonProps } from './Button'` — specifiers + module.
_BARREL = re.compile(r"export\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]")


def parse_barrel(barrel_text: str) -> list[dict]:
    """Primitives déclarées par le barrel : `{name, module}` (exports de VALEUR seuls ; `type X` ignorés)."""
    out: list[dict] = []
    for m in _BARREL.finditer(barrel_text):
        names = []
        for spec in m.group(1).split(","):
            spec = spec.strip()
            if not spec or spec.startswith("type "):
                continue
            names.append(spec.split(" as ")[0].strip())
        if names:
            out.append({"name": names[0], "module": m.group(2)})
    return out


def resolve_tsx(barrel_file: str, module: str) -> str:
    """Chemin POSIX relatif du `.tsx` d'une primitive, résolu depuis le dossier du barrel."""
    base = Path(barrel_file).parent
    return (base / (module.lstrip("./") + ".tsx")).as_posix()


class BarrelPrimitives:
    """Adaptateur primitives, convention barrel (`PrimitivesAdapter`)."""

    name = "barrel"

    def available(self, root: Path, cfg: Config) -> bool:
        return (Path(root) / cfg.primitives_barrel).is_file()

    def _entries(self, root: Path, cfg: Config) -> list[dict]:
        bpath = Path(root) / cfg.primitives_barrel
        if not bpath.is_file():
            return []
        return parse_barrel(bpath.read_text(encoding="utf-8"))

    def primitive_names(self, root: Path, cfg: Config) -> set[str]:
        return {e["name"] for e in self._entries(root, cfg)}

    def ui_dir(self, root: Path, cfg: Config) -> str:
        return Path(cfg.primitives_barrel).parent.as_posix()

    def detail_parser_available(self) -> bool:
        return tsparse.available()  # détail riche (props/variants) = grammaire TS/TSX (extra `[ts]`)

    def referenced_files(self, root: Path, cfg: Config) -> list[str]:
        bpath = Path(root) / cfg.primitives_barrel
        if not bpath.is_file():
            return []
        files = [cfg.primitives_barrel]
        for e in self._entries(root, cfg):
            tsx = resolve_tsx(cfg.primitives_barrel, e["module"])
            if (Path(root) / tsx).is_file():
                files.append(tsx)
        return files

    def consumed_primitives(self, text: str, importer_rel: str, cfg: Config,
                            names: set[str]) -> list[str]:
        d = Path(cfg.primitives_barrel).parent.as_posix()
        targets = {d, f"{d}/index"}
        found: set[str] = set()
        for source, imported in imports.named_imports(text):
            resolved = imports.resolve_module(source, importer_rel, cfg.web_root, cfg.import_alias)
            if resolved in targets:
                found.update(n for n in imported if n in names)
        return sorted(found)

    def extract_primitives(self, root: Path, cfg: Config) -> list[PrimitiveRow]:
        if not tsparse.available():   # le catalogue RICHE requiert tree-sitter (les noms, eux, non)
            return []
        rows: list[PrimitiveRow] = []
        for e in self._entries(root, cfg):
            tsx = resolve_tsx(cfg.primitives_barrel, e["module"])
            if not (Path(root) / tsx).is_file():
                continue
            det = tsx_component.detail(root, tsx, e["name"])
            rows.append({"name": e["name"], "file": tsx, "line": det["line"], "props": det["props"],
                         "variants": det["variants"], "defaults": det["defaults"], "lead": det["lead"]})
        return rows

    def missing_files(self, root: Path, cfg: Config) -> list[str]:
        out: list[str] = []
        for e in self._entries(root, cfg):
            tsx = resolve_tsx(cfg.primitives_barrel, e["module"])
            if not (Path(root) / tsx).is_file():
                out.append(f"{e['name']} ({tsx})")
        return out
