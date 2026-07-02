"""config — chargement de `.frontmap.toml` (configuration du repo cible).

Jumeau de `code-map`/`.codemap.toml` : une config **déclarative** à la racine du repo indexé pointe les
trois sources du design-system (tokens CSS, barrel de primitives, router). Absente → défauts génériques
calés sur les conventions cockpit. Les flags CLI surchargent la config. `tomllib` stdlib → zéro dépendance.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILENAME = ".frontmap.toml"
INDEX_DIRNAME = ".frontmap"  # index dérivés sous <root>/.frontmap/ (jumeau de code-map .codemap/)


@dataclass(frozen=True)
class Config:
    """Config résolue d'un repo cible (défauts = conventions cockpit : web/ Vite+React)."""

    tokens_file: str = "web/src/index.css"                      # source des tokens (@theme + :root)
    primitives_barrel: str = "web/src/components/ui/index.ts"   # barrel = liste canonique des primitives
    router_file: str = "web/src/router.tsx"                     # définition des routes (TanStack)
    web_root: str = "web/src"                                   # racine scannée : consommateurs (usage)

    @staticmethod
    def load(root: Path) -> Config:
        """Charge `<root>/.frontmap.toml` s'il existe, sinon renvoie les défauts."""
        p = Path(root) / CONFIG_FILENAME
        if not p.is_file():
            return Config()
        data = tomllib.loads(p.read_text(encoding="utf-8"))
        src = data.get("sources", {})
        d = Config()
        return Config(
            tokens_file=src.get("tokens", d.tokens_file),
            primitives_barrel=src.get("primitives_barrel", d.primitives_barrel),
            router_file=src.get("router", d.router_file),
            web_root=src.get("web_root", d.web_root),
        )
