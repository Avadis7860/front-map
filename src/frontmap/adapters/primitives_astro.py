"""primitives_astro — convention « astro » : un composant `.astro` par primitive (pas de barrel).

3ᵉ clé de l'axe primitives (après `barrel` et `dir-scan`), pour un design-system Astro. Autorité = le
**dossier** `components/ui/` (`Button.astro` = la primitive `Button`) ; nom canonique = **stem du fichier**
(pur filesystem, aucun parseur → `usage` marche sans les extras). Le détail (props/variants/defaults) vient du
**frontmatter TS** du composant, extrait par `astro_component` (grammaire astro pour délimiter, grammaire TS
pour parser). Consommation = import **par défaut** d'un fichier `.astro` (`import Button from
'@/components/ui/Button.astro'`) — l'extension `.astro` est explicite dans Astro/Vite, on la tolère.
"""
from __future__ import annotations

from pathlib import Path

from frontmap import astroparse, imports, tsparse
from frontmap.adapters import astro_component
from frontmap.adapters.base import PrimitiveRow
from frontmap.config import Config

_SUFFIX = ".astro"


def _is_primitive_file(p: Path) -> bool:
    return (p.suffix == _SUFFIX and p.is_file()
            and ".test." not in p.name and ".spec." not in p.name and not p.name.startswith("index."))


class AstroPrimitives:
    """Adaptateur primitives, convention Astro (`PrimitivesAdapter`)."""

    name = "astro"

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

    def detail_parser_available(self) -> bool:
        # le détail exige la grammaire astro (délimiter le frontmatter) ET la grammaire TS (le parser)
        return astroparse.available() and tsparse.available()

    def consumed_primitives(self, text: str, importer_rel: str, cfg: Config,
                            names: set[str]) -> list[str]:
        # astro : la primitive est l'export par défaut d'un fichier `.astro` → on suit les imports par défaut.
        # L'import Astro porte l'extension explicite (`…/Button.astro`) → on la retire avant de résoudre.
        d = self.ui_dir(root=Path("."), cfg=cfg)  # ui_dir ne dépend que de cfg
        found: set[str] = set()
        for source, _local in imports.default_imports(text):
            resolved = imports.resolve_module(source, importer_rel, cfg.web_root, cfg.import_alias)
            if resolved is None:
                continue
            if resolved.endswith(_SUFFIX):
                resolved = resolved[: -len(_SUFFIX)]
            stem = resolved[len(d) + 1:] if resolved.startswith(f"{d}/") else None
            if stem and stem in names:
                found.add(stem)
        return sorted(found)

    def extract_primitives(self, root: Path, cfg: Config) -> list[PrimitiveRow]:
        if not self.detail_parser_available():  # noms restent dispo sans les extras ; détail = tree-sitter
            return []
        rows: list[PrimitiveRow] = []
        for rel in self.referenced_files(root, cfg):
            name = Path(rel).stem
            det = astro_component.detail(root, rel, name)
            rows.append({"name": name, "file": rel, "line": det["line"], "props": det["props"],
                         "variants": det["variants"], "defaults": det["defaults"], "lead": det["lead"]})
        return rows

    def missing_files(self, root: Path, cfg: Config) -> list[str]:
        return []  # la source EST le fichier : pas de « déclaré mais absent » possible
