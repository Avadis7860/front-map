---
name: quality-gate
description: Gate qualité d'un package Python (ruff + mypy + pytest + déterminisme) — à passer VERT avant tout commit. Un rouge = on ne commit pas.
inputs: []
outputs: [rapport pass/fail par étage]
related_catalogs: [ruff, mypy, pytest]
---

# quality-gate — porte qualité avant commit

## Quand l'utiliser

Avant **chaque** commit (et avant tout merge). Prouve que le code est propre, typé, testé et
**déterministe**. C'est le Tier-0 déterministe : ce qu'un script voit, pas ce qu'un humain review.

## Procédure

```bash
VENV=.venv/bin        # activer le venv du projet d'abord si besoin
$VENV/ruff check src tests      # 1. lint + imports
$VENV/mypy                      # 2. types (config dans pyproject)
$VENV/pytest -q                 # 3. tests
```

1. **Lint** (`ruff check`) — style + imports + bugs simples. Rouge → corriger, jamais `# noqa` sans motif.
2. **Types** (`mypy`) — le package doit typer proprement. Une dép optionnelle non typée (tree-sitter) est
   déjà `ignore_missing_imports` — ne pas l'élargir.
3. **Tests** (`pytest`) — tout vert. Un test qui n'existe pas pour une capacité livrée = capacité non livrée.
4. **Déterminisme / idempotence** (dès que `frontmap build` est fonctionnel) — deux builds sur sources
   inchangées : le 2ᵉ **skip** (fraîcheur par hash de contenu, jamais mtime) et les index JSONL sont
   identiques :
   ```bash
   frontmap build --root <repo front>   # 1er : écrit tokens/primitives/routes/usage
   frontmap build --root <repo front>   # 2e : skip idempotent (sources inchangées)
   ```

## Sortie

Un rapport concis par étage (lint / types / tests / déterminisme) : **PASS** ou la première erreur.
**Tout doit être PASS** pour committer. Sinon : corriger la cause (pas déplacer un seuil), re-lancer.
