"""extractors — les extracteurs DS-sémantiques GÉNÉRIQUES de front-map (indépendants de la convention).

- `tokens` : design tokens depuis le CSS (@theme / :root) — stdlib pur, toujours dispo.
- `usage`  : index inverse « qui consomme quoi » — pur-Python, délègue la détection des primitives à
  l'adaptateur de convention résolu.

Les extracteurs SPÉCIFIQUES à une convention (router : tanstack/react-router ; primitives : barrel/dir-scan)
vivent dans `frontmap.adapters` (jumeau des *engines* de code-map). front-map ne re-duplique PAS l'extracteur
général `symindex` de code-map : il modélise ce que code-map ne modélise pas (la sémantique du design-system).
"""
from __future__ import annotations
