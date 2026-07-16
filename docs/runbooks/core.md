# core — runbook (le socle stdlib-pur vendorisé)

`src/frontmap/core/` — primitives sans dépendance, **vendorisées verbatim de code-map** (front-map n'en
dépend PAS à l'exécution, il en copie le socle). Résolution de racine, hash de fraîcheur, scoring lexical,
I/O JSONL. Chacune a une **source unique** (pas de copie divergente entre écriture et relecture).

## roots.project_root() / rel() — racine et chemin relatif

`src/frontmap/core/roots.py:22` (project_root), `:36` (rel) · appelés par `cli._resolve`, `build`, `query`.
`project_root` résout la racine dans l'ordre : `--root` explicite → `$FRONTMAP_ROOT` → remontée jusqu'au
premier dossier portant `.frontmap.toml` OU `.git/` → cwd. **Jamais de `parents[N]` fixe**. `rel` : chemin
POSIX relatif à la racine (clé d'identité stable d'un fichier dans l'index et le manifest).

## hashing.sha_text() — le hash de fraîcheur (source unique)

`src/frontmap/core/hashing.py:17` · appelé par `build._hashes` et `query.check`.
sha256 du texte UTF-8 (`errors="replace"`). **UN seul hash juge le dérivé** (écriture ET relecture). Les
appelants lisent en newline-universel (`Path.read_text` → CRLF traduit en LF) → même hash cross-OS quel
que soit `core.autocrlf`, ce qui rend le skip idempotent de `build` fiable.

## text.tokenize() / score() — le ranking lexical borné

`src/frontmap/core/text.py:30` (tokenize), `:43` (score) · appelés par `query.where`.
`tokenize` : accents repliés, minuscules, camelCase éclaté, mots-outils FR+EN retirés, dédup (hygiène
lexicale, pas d'IDF). `score` : borné `[0,1]` = `0.7 × couverture + 0.3 × bonus-nom`. Signature générique
(`name + haystack`) → score n'importe quel enregistrement (primitive/token). Cœur du classement de `where`.

## jsonl.read_jsonl() / write_jsonl() — I/O JSONL Unicode-safe

`src/frontmap/core/jsonl.py:16` (read), `:25` (write) · read par `query._load`, write par `build.build`.
Découpe sur `\n` **uniquement** (jamais `splitlines()`, qui casse sur U+2028/2029/0085 légitimes dans une
valeur JSON). Écrit une ligne/objet, UTF-8 `ensure_ascii=False`, LF forcé (cross-OS). Un seul point d'I/O
pour les 4 index → format stable.

## Zones non détaillées

- Helper `_fold`, constantes `_SPLIT`/`STOPWORDS` : lisibles inline. Socle identique à celui documenté
  dans docs-map `runbooks/core.md` (même vendoring code-map).
