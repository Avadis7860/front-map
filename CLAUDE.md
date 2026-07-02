# CLAUDE.md — front-map (index design-system déterministe, jumeau front de code-map)

> Lu au début de **chaque** session dans ce repo. Persona `tool-builder`.
> Ce fichier = **règles + index + outils**, PAS la spec. Le détail (mission, cadre verrouillé, schéma,
> frontière) vit dans `docs/` — **interroge-le** (`docsmap where`), ne le recopie pas ici.

## Règles (non négociables)

- **Boucle de travail** : tout changement passe par le skill **`work-loop`** — worktree `feature/<sujet>`
  créée **depuis `dev`**, gate vert, puis `dev` en ff-only. **`main` ne se travaille jamais** : il n'avance
  que promu depuis un `dev` vert. Jamais de commit direct sur `main`/`dev`.
- **Gate avant merge** : `ruff` + `mypy` + `pytest` + **idempotence** (skip sur sources inchangées) **verts**
  (skill `quality-gate`). Un acte irréversible (merge/destroy) = **feu vert humain, fail-closed**.
- **Anti-boucle** : pas de type de nœud tree-sitter inventé — le code de `tsparse.py` et de
  `code-map/engines/typescript_ts.py` est la référence. MCP `vault-catalogs` best-effort s'il est branché.
- **Anti-archéologie** : quand `frontmap` est fonctionnel sur un repo, interroge-le
  (`primitives`/`tokens`/`routes`/`usage`/`where`/`consumers`/`detect`) au lieu de grep le front ; et la
  prose de `docs/` se requête via `docsmap where`, jamais lue en bloc pour s'orienter.
- **Invariants du cœur** (détail dans `docs/architecture.md`) : cœur **stdlib-pur** (`re`/`tomllib`/`pathlib`
  — aucune dép obligatoire ; extraction **TSX** = extra `[ts]` tree-sitter à **dégradation gracieuse**, les
  **tokens CSS** restent toujours produits) · **jumeau de code-map, pas un fork** : vendorise le moteur
  *public* tree-sitter + une **copie** du socle `core/`, **ne dépend PAS** de code-map à l'exécution, **ne
  re-duplique PAS** son extracteur de symboles (front-map modélise la sémantique DS que code-map ne modélise
  pas) · **générique par adaptateurs** (router `tanstack`|`react-router` × primitives `barrel`|`dir-scan`,
  auto-détectés) au **schéma JSONL figé** · **fraîcheur par hash** (jamais mtime) · **jamais de cap
  silencieux** (dégradation signalée par `check`) · **rien de spécifique-projet en dur** (`.frontmap.toml`).
- Fixtures minuscules, mini `web/` d'échantillon (**jamais** un vrai fichier d'un projet réel).

## Index (interroge, ne lis pas en bloc)

La spec vit dans `docs/`. **Ne la lis pas en bloc pour t'orienter** — `docs-map` (injecté, zéro-dép) répond
à l'intention ; lis ensuite **seulement** la tranche `fichier:lignes` renvoyée :

```
docsmap where "<intention>"     # → docs/…:lignes de la section pertinente
docsmap sections                # table des matières
```

Ce que couvre la doc (cibles de `docsmap where`) :

- `docs/architecture.md` — intention, les 4 extracteurs (tokens/primitives/routes/usage), le **modèle
  d'adaptateurs** (2 axes orthogonaux), la **frontière verrouillée** vis-à-vis de code-map, le CLI.

## Outils à disposition (embarqués dans ce repo)

- **Skills** (`.claude/skills/`) : `work-loop` (boucle de travail sûre, lightweight, sans cockpit) ·
  `quality-gate` (ruff + mypy + pytest + idempotence) · `port-tool` (ajout de module au schéma figé).
- **Hook** (`.claude/hooks/post-edit-check.py`) : `py_compile` + `ruff` sur le `.py` touché à chaque édition.
- **Persona** (`.claude/output-styles/tool-builder.md`) : posture outilleur déterministe.
- **Auto-carte** : `frontmap primitives/tokens/routes/usage/consumers/detect/check` sur un repo front.
- **Carte de doc** : `docsmap where/sections/read/check` sur la prose `docs/` de ce repo (injecté, zéro-dép).
- **Doc tierce** : MCP `vault-catalogs` (`query_catalog` scopé, `read_doc`) s'il est branché.

## Rapport au cockpit (auto-travaillable seul)

Ce repo est **auto-travaillable en autonomie légère** : un clone GitHub suffit pour qu'un worker — IA
`claude` **ou** humain — le fasse évoluer en sûreté via `work-loop`, **sans aucun centre de contrôle**. Le
**cockpit** (forge : dispatch multi-projet, DB, gate, web) **automatise** exactement cette boucle par-dessus ;
il est **optionnel**, jamais requis. Les invariants sont les **mêmes des deux côtés** : travail sur worktree
`feature` depuis `dev`, gate vert avant merge, `main` protégé, **GO humain sur tout acte irréversible**.
