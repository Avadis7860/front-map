"""frontmap — index **design-system** déterministe et interrogeable par un agent.

Jumeau de `code-map`, côté front : là où code-map répond « où est le code / qui appelle quoi », front-map
répond « quelle **primitive** / quel **token** / quelle **route** pour X ? ». Il lit le `web/` d'un projet
et écrit trois index JSONL (tokens, primitives, routes). Cœur stdlib-pur (tokens = CSS) ; l'extraction
TSX (primitives/routes) est un **extra optionnel** via `tree-sitter` (absent → dégradation gracieuse).

Voir `docs/architecture.md` pour la frontière avec code-map et le contrat de schéma.
"""
from __future__ import annotations

__version__ = "0.1.0"
