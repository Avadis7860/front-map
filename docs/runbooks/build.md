# build — runbook (writer unique des index)

`src/frontmap/build.py` — orchestre les extracteurs via les **adaptateurs de convention**, écrit les 4
index JSONL (`tokens/primitives/routes/usage`), gère la **fraîcheur par hash**. `build` écrit, `query`
lit (invariant jumeau de code-map). Contrat : `CONTRACT_VERSION = "frontmap-index-v1"`.

## build() — (re)construit les 4 index, skip idempotent

`src/frontmap/build.py:57` · appelé par `cli._cmd_build`.
Entrées : `root, index_dir, cfg, *, force=False`. Résout router + primitives (`adapters.resolve_*`),
calcule `conventions={router,primitives}`, hache les sources. **Skip idempotent** si le manifest a les
mêmes `file_hashes` ET `ts_available` ET `conventions` (une convention qui change doit reparser — même
garde que code-map sur `available`). Sinon extrait : `tokens.extract_tokens`, `prim.extract_primitives`,
`router.extract_routes`, puis `usage.extract_usage` — et écrit `tokens/primitives/routes/usage.jsonl` +
`frontmap.manifest.json` (`sort_keys` → déterministe). Sortie : dict `{skipped, counts, ts_available,
conventions, index}`. **Invariant clé** : `usage` reçoit les **noms** de primitives via l'adaptateur
(regex/filesystem), PAS via `prim_rows` — donc l'index inverse reste exploitable **sans l'extra `[ts]`**
(tokens CSS et usage toujours produits ; seul le catalogue riche props/variants requiert tree-sitter).

## source_files() — la base du hash de fraîcheur

`src/frontmap/build.py:26` · appelé par `build` et `query.check`.
Entrées : `root, cfg`. Sortie : `list[str]` **dédupliquée, ordre stable**. Passe par les adaptateurs
résolus (`prim.referenced_files`, `router.referenced_files`, `usage.consumer_files`) + le fichier de
tokens. C'est l'ensemble exact des fichiers hachés → ce qui déclenche/évite un rebuild.

## _hashes() / _read() — I/O de fraîcheur

`src/frontmap/build.py:47` (_hashes), `:52` (_read) · appelés par `build`.
`_hashes` : `{rel → sha_text(contenu)}` (lecture newline-universelle, `errors="replace"`). `_read` :
contenu d'un fichier ou `""` s'il manque (tokens_file optionnel). Alimentent le manifest et l'extraction.

## Zones non détaillées

- Le **pourquoi** de l'invariant build/query et du modèle multi-convention : `docs/architecture.md`
  (`docsmap where "couches"` / `"frontière avec code-map"`).
- La résolution d'adaptateur elle-même : voir `runbooks/adapters.md`.
