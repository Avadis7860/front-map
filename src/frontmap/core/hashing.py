"""hashing — hash de fraîcheur partagé (socle stdlib-pur).

SOURCE UNIQUE du sha256-de-texte qui alimente le manifest de fraîcheur des index dérivés
(`frontmap.manifest.json`) et sa relecture. UN seul hash juge tous les dérivés → pas de copies
divergentes entre écriture et relecture.

Vendorisé **verbatim** de `code-map` (`codemap/core/hashing.py`) — front-map ne dépend PAS de code-map
à l'exécution ; il en copie le socle stdlib-pur. Correctif multi-OS : le texte hashé est lu en
newline-universel par les appelants (`Path.read_text()` traduit CRLF→LF), donc le même fichier produit
le même hash sur WSL / Debian / macOS quel que soit `git core.autocrlf`.
"""
from __future__ import annotations

import hashlib


def sha_text(text: str) -> str:
    """sha256 hexdigest du texte encodé UTF-8 (errors=replace → total sur tout contenu)."""
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()
