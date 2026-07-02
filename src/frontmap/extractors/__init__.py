"""extractors — les trois extracteurs DS-sémantiques de front-map.

- `tokens`     : design tokens depuis le CSS (@theme / :root) — stdlib pur, toujours dispo.
- `primitives` : catalogue de primitives depuis le barrel + TSX — tree-sitter (best-effort).
- `routes`     : arbre des routes depuis le router TSX — tree-sitter (best-effort).

Chacun est étroit et purpose-built : front-map ne re-duplique PAS l'extracteur général `symindex` de
code-map, il modélise ce que code-map ne modélise pas (la sémantique du design-system).
"""
from __future__ import annotations
