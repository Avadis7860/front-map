# extractors — runbook (tokens CSS + graphe d'usage)

`src/frontmap/extractors/` — les deux extracteurs **pur-Python** (toujours disponibles, sans
tree-sitter) : les design tokens depuis le CSS, et l'index inverse de consommation du DS.

## extract_tokens() — les design tokens depuis le CSS

`src/frontmap/extractors/tokens.py:77` · appelé par `build.build`.
Entrées : `css_text, source_file`. Sortie : `list[dict]` `{name, value, group, source_file, line, lead}`,
déterministe. Parse les custom properties (`--x: v;`) des blocs `@theme`/`:root` (`_iter_code_lines`
retire les commentaires `/* */`, y compris multilignes, et retient le titre de section courant). **Zéro
tree-sitter** → toujours produit. Le `group` (via `group_of`) donne la sémantique que code-map ne modélise
pas.

## group_of() — le groupe sémantique d'un token

`src/frontmap/extractors/tokens.py:21` · appelé par `extract_tokens`.
Dérive le groupe du **préfixe** du nom : `--color-accent-*`→`accent` ; `--color-{ok,warn,danger,info,
purple}-*`→`status` ; autres `--color-*`→`surface` ; `--radius-*`→`radius` ; `--shadow-*`→`shadow` ;
`--animate-*`→`motion` ; `--font-*`→`typography` ; `--z-*`→`z` ; sinon `other`. C'est le filtre du verbe
`tokens --group`.

## extract_usage() — l'index inverse « qui consomme le DS »

`src/frontmap/extractors/usage.py:91` · appelé par `build.build`.
Entrées : `root, cfg, prim, primitive_names, token_names, routes_rows`. Pour chaque fichier consommateur
(`consumer_files`), détecte les **primitives** consommées (délégué à `prim.consumed_primitives` →
générique par convention) et les **tokens** référencés littéralement (`_token_refs`, frontière de mot).
Un fichier sans aucune primitive ni token est omis. Enrichit d'un lien **route** (`_route_by_file`) si le
fichier est le composant d'une route. Sortie triée `{consumer, kind, primitives, tokens, route}`.
**Pur-Python** : marche sans `[ts]` (les noms viennent de l'adaptateur) ; seul le lien route se dégrade à
vide quand `routes` est vide. Ce n'est PAS un graphe d'imports général (ça, c'est code-map) — uniquement
les consommateurs du vocabulaire déjà connu de front-map.

## consumer_files() — les fichiers scannés comme consommateurs

`src/frontmap/extractors/usage.py:39` · appelé par `extract_usage` et `build.source_files`.
Fichiers `.tsx`/`.ts` sous `web_root`, **hors** primitives (`ui_dir`), router, tests, `.d.ts`. Triés
(déterminisme + base du hash). Définit le périmètre de l'analyse d'usage.

## Zones non détaillées

- Helpers `_section_title`, `_iter_code_lines`, `_token_refs`, `_route_by_file` : mécanique interne
  (parsing CSS ligne à ligne, résolution route→fichier via `imports`). Voir `runbooks/ts-layer.md` pour
  la résolution d'imports sous-jacente.
