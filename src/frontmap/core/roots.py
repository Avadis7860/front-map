"""roots — résolution générique de la racine d'un repo cible.

Vendorisé de `code-map` (`codemap/core/roots.py`), repère adapté à front-map. On résout la racine de
n'importe quel repo, dans l'ordre :

    1. `--root` explicite (le plus spécifique) ;
    2. `$FRONTMAP_ROOT` (posé par un déploiement / le cockpit) ;
    3. remontée depuis `start` (ou le cwd) jusqu'au premier répertoire-repère contenant
       `.frontmap.toml` OU `.git/` ;
    4. sinon, `start` (ou cwd) tel quel.

Ne code JAMAIS un `parents[N]` fixe.
"""
from __future__ import annotations

import os
from pathlib import Path

_MARKERS = (".frontmap.toml", ".git")


def project_root(explicit: Path | str | None = None, start: Path | None = None) -> Path:
    """Racine du repo cible (voir ordre de priorité dans le docstring du module)."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("FRONTMAP_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        if any((d / m).exists() for m in _MARKERS):
            return d
    return here


def rel(root: Path, p: Path) -> str:
    """Chemin de `p` relatif à `root` en POSIX, ou `p` tel quel si hors de `root`."""
    try:
        return Path(p).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(p)
