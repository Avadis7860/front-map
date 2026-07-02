"""primitives_dirscan — convention « dir-scan » : pas de barrel, un fichier `.tsx` par primitive.

Autorité = le **dossier** `components/ui/` (`Button.tsx` = la primitive `Button`, `export default`).
Consommation = import **par défaut** résolvant vers un fichier de primitive
(`import Button from '@/components/ui/Button'`). C'est la convention du web aggregator (react-router). Le
nom canonique = le **stem du fichier** (aligné sur le chemin d'import, robuste). `primitive_names` est pur
filesystem (aucun tree-sitter) ; le détail props passe par `tsx_component` (best-effort).
"""
from __future__ import annotations

from pathlib import Path

from frontmap import imports, tsparse
from frontmap.adapters import tsx_component
from frontmap.adapters.base import PrimitiveRow
from frontmap.config import Config

_SUFFIX = ".tsx"


def _is_primitive_file(p: Path) -> bool:
    return (p.suffix == _SUFFIX and p.is_file()
            and ".test." not in p.name and ".spec." not in p.name and not p.name.startswith("index."))


class DirScanPrimitives:
    """Adaptateur primitives, convention scan-de-dossier (`PrimitivesAdapter`)."""

    name = "dir-scan"

    def _dir(self, root: Path, cfg: Config) -> Path:
        return Path(root) / cfg.primitives_dir

    def available(self, root: Path, cfg: Config) -> bool:
        d = self._dir(root, cfg)
        return d.is_dir() and any(_is_primitive_file(p) for p in d.iterdir())

    def _files(self, root: Path, cfg: Config) -> list[Path]:
        d = self._dir(root, cfg)
        if not d.is_dir():
            return []
        return sorted((p for p in d.iterdir() if _is_primitive_file(p)), key=lambda p: p.name)

    def ui_dir(self, root: Path, cfg: Config) -> str:
        return cfg.primitives_dir.rstrip("/")

    def primitive_names(self, root: Path, cfg: Config) -> set[str]:
        return {p.stem for p in self._files(root, cfg)}

    def referenced_files(self, root: Path, cfg: Config) -> list[str]:
        return [f"{self.ui_dir(root, cfg)}/{p.name}" for p in self._files(root, cfg)]

    def _target_map(self, root: Path, cfg: Config) -> dict[str, str]:
        """{chemin rel sans extension → nom de primitive} pour résoudre un import de fichier."""
        d = self.ui_dir(root, cfg)
        return {f"{d}/{p.stem}": p.stem for p in self._files(root, cfg)}

    def consumed_primitives(self, text: str, importer_rel: str, cfg: Config,
                            names: set[str]) -> list[str]:
        # dir-scan : la primitive est l'export PAR DÉFAUT → on suit les imports par défaut vers un fichier
        # de primitive. Un import nommé depuis ce fichier viserait un symbole secondaire (type/helper), pas
        # la primitive → ignoré.
        d = self.ui_dir(root=Path("."), cfg=cfg)  # ui_dir ne dépend que de cfg
        found: set[str] = set()
        for source, _local in imports.default_imports(text):
            resolved = imports.resolve_module(source, importer_rel, cfg.web_root, cfg.import_alias)
            if resolved is None:
                continue
            stem = resolved[len(d) + 1:] if resolved.startswith(f"{d}/") else None
            if stem and stem in names:
                found.add(stem)
        return sorted(found)

    def extract_primitives(self, root: Path, cfg: Config) -> list[PrimitiveRow]:
        if not tsparse.available():   # catalogue riche = tree-sitter ; `primitive_names` reste dispo sans
            return []
        rows: list[PrimitiveRow] = []
        for rel in self.referenced_files(root, cfg):
            name = Path(rel).stem
            det = tsx_component.detail(root, rel, name)
            rows.append({"name": name, "file": rel, "line": det["line"], "props": det["props"],
                         "variants": det["variants"], "defaults": det["defaults"], "lead": det["lead"]})
        return rows

    def missing_files(self, root: Path, cfg: Config) -> list[str]:
        return []  # la source EST le fichier : pas de « déclaré mais absent » possible
