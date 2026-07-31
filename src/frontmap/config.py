"""config — chargement de `.frontmap.toml` (configuration du repo cible).

Jumeau de `code-map`/`.codemap.toml` : une config **déclarative** à la racine du repo indexé pointe les
sources du design-system (tokens CSS, primitives, router) et, depuis la genericité multi-convention, les
**axes de convention** (`router` : tanstack | react-router ; `primitives` : barrel | dir-scan). Absente →
défauts génériques + auto-détection. Les flags CLI surchargent la config. `tomllib` stdlib → zéro dépendance.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILENAME = ".frontmap.toml"
INDEX_DIRNAME = ".frontmap"  # index dérivés sous <root>/.frontmap/ (jumeau de code-map .codemap/)

ROUTER_FLAVORS = ("auto", "tanstack", "react-router")
PRIMITIVES_SOURCES = ("auto", "barrel", "dir-scan", "astro")


@dataclass(frozen=True)
class Config:
    """Config résolue d'un repo cible (défauts = conventions cockpit : web/ Vite+React+TanStack+barrel).

    Les champs `router_flavor`/`primitives_source` valent `"auto"` par défaut → détection à partir du code
    (cf. `adapters.detect_router`/`detect_primitives`). Un `.frontmap.toml` peut forcer une convention."""

    tokens_file: str = "web/src/index.css"                      # source des tokens (@theme + :root)
    primitives_barrel: str = "web/src/components/ui/index.ts"   # barrel (convention `barrel`)
    primitives_dir: str = "web/src/components/ui"               # dossier primitives (convention `dir-scan`)
    router_file: str = "web/src/router.tsx"                     # définition des routes
    web_root: str = "web/src"                                   # racine scannée : consommateurs (usage)
    import_alias: str = "@/"                                    # alias import → web_root (Vite/tsconfig)
    router_flavor: str = "auto"                                 # auto | tanstack | react-router
    primitives_source: str = "auto"                            # auto | barrel | dir-scan

    @staticmethod
    def load(root: Path) -> Config:
        """Charge `<root>/.frontmap.toml` s'il existe, sinon renvoie les défauts."""
        p = Path(root) / CONFIG_FILENAME
        if not p.is_file():
            return Config()
        data = tomllib.loads(p.read_text(encoding="utf-8"))
        src = data.get("sources", {})
        conv = data.get("conventions", {})
        d = Config()
        return Config(
            tokens_file=src.get("tokens", d.tokens_file),
            primitives_barrel=src.get("primitives_barrel", d.primitives_barrel),
            primitives_dir=src.get("primitives_dir", d.primitives_dir),
            router_file=src.get("router", d.router_file),
            web_root=src.get("web_root", d.web_root),
            import_alias=src.get("alias", d.import_alias),
            router_flavor=conv.get("router", d.router_flavor),
            primitives_source=conv.get("primitives", d.primitives_source),
        )
