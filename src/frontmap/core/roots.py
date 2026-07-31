"""roots — résolution générique de la racine d'un repo cible.

Vendorisé de `code-map` (`codemap/core/roots.py`), repère adapté à front-map. On résout la racine de
n'importe quel repo, dans l'ordre :

    1. `--root` explicite (le plus spécifique) ;
    2. `$FRONTMAP_ROOT` (posé par un déploiement / le cockpit) ;
    3. remontée depuis `start` (ou le cwd) jusqu'au premier répertoire-repère contenant
       `.frontmap.toml` OU `.git/` ;
    4. sinon, `start` (ou cwd) tel quel.

Ne code JAMAIS un `parents[N]` fixe.

Porte aussi `main_worktree_root` : les index dérivés ne sont pas versionnés, donc `git worktree add` ne les
emporte pas — un consommateur en worktree doit pouvoir emprunter ceux du répertoire de travail principal.
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


def main_worktree_root(root: Path | str) -> Path | None:
    """Racine du répertoire de travail **principal** si `root` est une worktree git LIÉE, sinon `None`.

    Une worktree liée porte un `.git` **fichier** (`gitdir: <chemin>`) au lieu d'un répertoire ; le
    répertoire pointé contient un fichier `commondir` désignant le `.git` **partagé**, dont le parent est la
    racine principale. Lecture **stdlib pure**, aucun sous-processus `git` : le cœur reste sans dépendance
    obligatoire (l'outil répond sur un checkout où git n'est pas installé) et les tests n'ont pas besoin d'un
    vrai dépôt.

    **Fail-soft intégral** — toute déviation rend `None`, jamais une racine devinée : `.git` répertoire (repo
    normal) ou absent · gitfile illisible ou sans préfixe `gitdir:` · `commondir` absent · `.git` commun qui
    ne s'appelle pas `.git` (dépôt nu, `--separate-git-dir` : il n'y a alors pas de worktree principale à
    désigner). L'appelant retombe sur son comportement habituel.
    """
    base = Path(root)
    dotgit = base / ".git"
    if not dotgit.is_file():
        return None
    try:
        pointer = dotgit.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not pointer.startswith("gitdir:"):
        return None
    gitdir = Path(pointer[len("gitdir:"):].strip())
    if not gitdir.is_absolute():
        gitdir = base / gitdir
    try:
        common = Path((gitdir / "commondir").read_text(encoding="utf-8").strip())
    except OSError:
        return None
    if not common.is_absolute():
        common = gitdir / common
    common = Path(os.path.normpath(common))  # normalise `../..` SANS toucher au disque (pas de resolve)
    if common.name != ".git":
        return None
    return common.parent


def rel(root: Path, p: Path) -> str:
    """Chemin de `p` relatif à `root` en POSIX, ou `p` tel quel si hors de `root`."""
    try:
        return Path(p).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(p)
