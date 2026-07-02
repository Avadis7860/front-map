---
name: port-tool
description: Porte un outil legacy (source vault) dans son emplacement de package, en appliquant le correctif de point faible documenté + un test. LE workflow récurrent d'extraction.
inputs: [module-cible]
outputs: [module porté, test, PORTING.md à jour]
related_catalogs: []
---

# port-tool — porter un outil dans son emplacement propre

## Quand l'utiliser

À chaque étape de l'extraction *outil par outil* : un stub `raise NotImplementedError("port: <source>
— #N")` doit devenir du code réel. Vaut aussi pour tout repo frère qui extrait du legacy (mcp-catalogs).

## Procédure

1. **Cible.** Ouvre le module à porter (ex. `src/frontmap/adapters/router_react.py`). Lis son docstring et sa
   ligne `NotImplementedError("port: <fichier source> — #N")` : elle nomme la **source** et le **correctif**.
2. **Lis la source + le correctif.** Ouvre le fichier source legacy nommé, ET la ligne `#N` de
   `docs/weak-points.md`. Le correctif dit *quoi changer* en portant (imports relatifs, config-driven, plus
   de couplage vault, etc.). **Ne recopie pas tel quel** — applique le fix.
3. **Anti-boucle.** Avant une API non triviale (stdlib `ast`/tree-sitter/`tomllib`), vérifie la signature
   dans la stdlib / le code — jamais « de mémoire ».
4. **Porte.** Écris le code dans le slot. Respecte : schéma de sortie **figé** (`docs/schema-contract.md`),
   zéro cap silencieux, `from __future__ import annotations`, imports de package (`from frontmap.core import
   …`), aucun chemin en dur. Scaffold : `.claude/templates/module.py.tmpl`.
5. **Teste.** Ajoute/complète un test fixture-based (`.claude/templates/test_module.py.tmpl`) : correction
   sur `tests/fixtures/`, + une assertion de **déterminisme** si le module produit un index. Noms fictifs
   only dans les fixtures.
6. **Gate.** Lance le skill `quality-gate` (ruff + mypy + pytest + déterminisme). Tout vert.
7. **Journal.** Coche la ligne du module dans `PORTING.md` (source, correctif appliqué, test).

## Garde-fous

- Un module porté qui casse le schéma figé sans bump de version = à refuser.
- Une dépendance obligatoire ajoutée au cœur = à refuser (le cœur reste stdlib-pur ; lib = extra optionnel).
- Si le port révèle un point faible non listé → l'ajouter à `docs/weak-points.md` avant de continuer.
