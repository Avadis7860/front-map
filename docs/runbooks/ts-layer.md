# ts-layer — runbook (parsing tree-sitter + résolution d'imports)

Les deux modules qui portent l'accès au TS/TSX. `tsparse` : le parser tree-sitter partagé, **à
dégradation gracieuse**. `imports` : parsing léger (regex) des imports ES, partagé par usage + adaptateurs.

## tsparse.available() — tree-sitter est-il installé ?

`src/frontmap/tsparse.py:39` · appelé par `build`, `query.check`, chaque extracteur TS.
Sortie : `bool`. True si l'extra `[ts]` (`tree_sitter` + `tree_sitter_typescript`) est présent. **C'est le
point de dégradation gracieuse unique** : quand False, tous les extracteurs qui en dépendent (primitives
riches, routes) rendent une liste vide — jamais d'exception. Les tokens CSS et les noms de primitives
(regex) restent produits.

## tsparse._parsers() — chargement LAZY, une seule fois

`src/frontmap/tsparse.py:21` · appelé par `available` et `parse`.
Construit `{lang → Parser}` au premier appel (mémoïsé dans `_PARSERS`). `try/except` sur l'import :
lib absente → `_PARSERS = {}` et renvoie None (best-effort). front-map **vendorise le moteur public**
tree-sitter (même dép optionnelle que code-map) ; il ne ré-implémente pas `symindex`.

## tsparse.parse() — source → (root_node, data_bytes)

`src/frontmap/tsparse.py:44` · appelé par les extracteurs TS.
Entrées : `src, rel`. Choisit la grammaire par suffixe (`_LANG_OF` : tsx/typescript), encode en octets
(tree-sitter indexe par **offsets d'octets** → `data` accompagne toujours le nœud), parse. None si TS
absent ou parse KO. Toutes les lectures d'AST partent de là.

## tsparse — les accesseurs de nœud

`src/frontmap/tsparse.py:60` (node_text), `:65` (field), `:70` (name_of), `:76` (lead_comment), `:91`
(unwrap_export).
`node_text` : slice d'octets → str. `field` : enfant nommé (`child_by_field_name`). `name_of` : valeur du
champ `name`. `lead_comment` : 1re ligne utile d'un JSDoc/`//` précédant une déclaration (≤80c, `@tags`
sautés). `unwrap_export` : remonte au `export_statement` parent (pour lire le JSDoc posé avant `export`).
Socle partagé par tous les adaptateurs TS.

## imports.resolve_module() — chemin rel d'un import LOCAL

`src/frontmap/imports.py:21` · appelé par les adaptateurs primitives + `usage`.
Entrées : `source, importer_rel, web_root, alias="@/"`. `<alias>x`→`<web_root>/x` ; `./x`/`../x` relatif
au fichier importateur ; **None** pour un package nu (`react`, `@tanstack/…` — non local). Sortie : chemin
rel POSIX **sans extension**. C'est ce qui relie un import au vocabulaire connu.

## imports.named_imports() / default_imports() — les deux formes suivies

`src/frontmap/imports.py:34` (named), `:50` (default).
`named_imports` : `(source, [noms de valeur])` par `import { … } from '…'` — type-only ignoré (convention
barrel). `default_imports` : `(source, nom_local)` par `import X from '…'` (convention dir-scan). Regex, pas
de tree-sitter → l'index inverse reste exploitable sans l'extra `[ts]`. front-map ne modélise PAS le graphe
d'imports général (ça, c'est code-map) : uniquement ces deux formes.

## Zones non détaillées

- Constantes `_LANG_OF`, `_NAMED`, `_DEFAULT` : lisibles inline. Le *pourquoi* de la dégradation gracieuse
  et de la frontière avec code-map : `docs/architecture.md` (`docsmap where "dégradation gracieuse"`).
