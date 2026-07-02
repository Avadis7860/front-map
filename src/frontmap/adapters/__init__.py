"""adapters — registres des adaptateurs de convention + détection/résolution par repo.

Jumeau de `code-map/engines/__init__.py`, sur DEUX axes orthogonaux (router, primitives). Chaque registre
mappe une clé de convention → instance d'adaptateur. `detect_*` inspecte le code (imports du router,
présence d'un barrel vs d'un dossier) pour choisir ; `resolve_*` honore un override `.frontmap.toml` sinon
auto-détecte. Un adaptateur reste TOUJOURS dans le registre même si tree-sitter est absent : la détection
se fait par présence de fichiers, l'extraction dégrade (liste vide). La convention retenue est tracée au
manifest (cf. build) — jamais devinée en silence.
"""
from __future__ import annotations

from pathlib import Path

from frontmap.adapters.base import PrimitivesAdapter, RouterAdapter
from frontmap.adapters.primitives_barrel import BarrelPrimitives
from frontmap.adapters.primitives_dirscan import DirScanPrimitives
from frontmap.adapters.router_react import ReactRouter
from frontmap.adapters.router_tanstack import TanstackRouter
from frontmap.config import Config


def router_registry() -> dict[str, RouterAdapter]:
    return {"tanstack": TanstackRouter(), "react-router": ReactRouter()}


def primitives_registry() -> dict[str, PrimitivesAdapter]:
    return {"barrel": BarrelPrimitives(), "dir-scan": DirScanPrimitives()}


def detect_router(root: Path, cfg: Config) -> str:
    """Convention de routing sniffée depuis les imports du `router_file`. Défaut `tanstack` (back-compat)."""
    fpath = Path(root) / cfg.router_file
    if fpath.is_file():
        text = fpath.read_text(encoding="utf-8", errors="replace")
        if "@tanstack/react-router" in text:
            return "tanstack"
        if "react-router" in text:
            return "react-router"
    return "tanstack"


def detect_primitives(root: Path, cfg: Config) -> str:
    """`barrel` si le barrel existe ; sinon `dir-scan` si le dossier a des `.tsx` ; sinon `barrel`."""
    if (Path(root) / cfg.primitives_barrel).is_file():
        return "barrel"
    if DirScanPrimitives().available(root, cfg):
        return "dir-scan"
    return "barrel"


def resolve_router(root: Path, cfg: Config) -> RouterAdapter:
    flavor = cfg.router_flavor if cfg.router_flavor != "auto" else detect_router(root, cfg)
    return router_registry().get(flavor, TanstackRouter())


def resolve_primitives(root: Path, cfg: Config) -> PrimitivesAdapter:
    src = cfg.primitives_source if cfg.primitives_source != "auto" else detect_primitives(root, cfg)
    return primitives_registry().get(src, BarrelPrimitives())


def detect(root: Path, cfg: Config) -> dict:
    """Conventions retenues pour un repo (auto-détection ou override) + leur disponibilité."""
    rt, pr = resolve_router(root, cfg), resolve_primitives(root, cfg)
    return {
        "router": rt.name, "router_available": rt.available(root, cfg),
        "primitives": pr.name, "primitives_available": pr.available(root, cfg),
    }
