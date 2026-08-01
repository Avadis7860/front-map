# adapters — runbook (le cœur générique-par-adaptateur)

`src/frontmap/adapters/` — là où code-map varie par **langage**, front-map varie par **convention** sur
DEUX axes orthogonaux : le *router* (comment les routes sont déclarées) et les *primitives* (comment le
catalogue DS est exposé). Chaque axe a son `Protocol` (schéma de sortie **figé**) ; un projet compose un
adaptateur de chaque, auto-détecté ou forcé. Contrat best-effort commun : `[]`/`set()` si source absente
ou tree-sitter manquant — **jamais d'exception**. Trois conventions primitives : `barrel`, `dir-scan`, `astro`.

## resolve_router() / resolve_primitives() — choisir l'adaptateur

`src/frontmap/adapters/__init__.py:56` (router), `:61` (primitives) · appelés par `build`, `query`.
Entrées : `root, cfg`. Honorent l'override `.frontmap.toml` (`cfg.router_flavor`/`primitives_source`)
sinon délèguent à `detect_*`. Retournent l'instance depuis le registre (`router_registry` /
`primitives_registry` : `barrel`|`dir-scan`|`astro`), avec fallback sûr (`TanstackRouter` /
`BarrelPrimitives`). Point d'entrée de toute la généricité : le reste du code parle aux Protocols, jamais
à une convention en dur.

## detect_router() / detect_primitives() — auto-détection par le code

`src/frontmap/adapters/__init__.py:31` (router), `:43` (primitives) · appelés par `resolve_*` et `detect`.
`detect_router` sniffe les imports du `router_file` (`@tanstack/react-router` → `tanstack` ;
`react-router` → `react-router` ; défaut `tanstack`). `detect_primitives` : `barrel` si le barrel
existe, sinon `dir-scan` si le dossier a des `.tsx`, sinon `astro` si le dossier a des `.astro`, sinon
`barrel`. L'ordre garde barrel/dir-scan prioritaires (aucun projet TSX ne bascule en astro par erreur).
La convention retenue est **tracée au manifest** (build) — jamais devinée en silence.

## detect() — conventions retenues + disponibilité

`src/frontmap/adapters/__init__.py:66` · appelé par `cli._cmd_detect`.
Renvoie `{router, router_available, primitives, primitives_available}` — ce que le verbe `frontmap
detect` expose pour diagnostiquer un repo cible.

## RouterAdapter / PrimitivesAdapter — les Protocols (schéma figé)

`src/frontmap/adapters/base.py:48` (router), `:63` (primitives) ; rows `RouteRow` `:21`, `PrimitiveRow`
`:35`.
Les Protocols que tout adaptateur remplit. `RouterAdapter` : `available`, `extract_routes` (remplit
`RouteRow`), `referenced_files`, `signals` (limites connues). `PrimitivesAdapter` : `primitive_names`
(**contrat pivot** — regex/filesystem, sans tree-sitter → `usage` marche sans extra), `consumed_primitives`
(encapsule comment CETTE convention importe une primitive), `ui_dir`, `detail_parser_available` (la grammaire
requise pour le détail riche est-elle chargeable ? → alimente `primitives_status` de `check`),
`extract_primitives`, `missing_files`, `available`. `RouteRow`/`PrimitiveRow` sont les schémas JSONL figés
(comme le `Symbol` de code-map) : les adaptateurs les remplissent, les consommateurs ne cassent jamais.

## BarrelPrimitives — convention barrel

`src/frontmap/adapters/primitives_barrel.py:43` (classe) ; `parse_barrel` `:22`, `resolve_tsx` `:37`.
Autorité = `components/ui/index.ts` qui ré-exporte (`export { Button } from './Button'`). `parse_barrel`
extrait les exports de **valeur** (les `type X` ignorés) ; `primitive_names` = leurs noms (regex, sans
TS). `consumed_primitives` suit les imports **nommés** vers le dossier du barrel. `extract_primitives`
enrichit via `tsx_component.detail` (vide sans tree-sitter). `missing_files` = primitive déclarée dont le
`.tsx` manque. Convention du nouveau cockpit (TanStack).

## DirScanPrimitives — convention dir-scan

`src/frontmap/adapters/primitives_dirscan.py:26` (classe) ; `_is_primitive_file` `:21`.
Autorité = le **dossier** `components/ui/` (`Button.tsx` = primitive `Button`, `export default`). Nom
canonique = **stem du fichier** (aligné sur le chemin d'import). `consumed_primitives` suit les imports
**par défaut** résolvant vers un fichier de primitive. `missing_files` = toujours `[]` (la source EST le
fichier). `detail_parser_available` = `tsparse.available()`. Convention du web aggregator (react-router).

## AstroPrimitives — convention astro

`src/frontmap/adapters/primitives_astro.py:27` (classe) ; `_is_primitive_file` `:22`.
Autorité = le **dossier** `components/ui/` (`Button.astro` = primitive `Button`). Nom canonique = **stem**
(filesystem, sans parseur → `primitive_names` marche sans extra). Le détail (props/variants/defaults) vient
du **frontmatter** TS, extrait par `astro_component.detail` (grammaire astro pour délimiter, grammaire TS
pour parser — *injection de langage*). `consumed_primitives` suit les imports **par défaut** en tolérant
l'extension `.astro` explicite (Astro/Vite). `detail_parser_available` = `astroparse.available() AND
tsparse.available()` (le détail exige les DEUX). `missing_files` = `[]`. Convention d'une vitrine Astro.

## astroparse — grammaire astro (délimite le frontmatter)

`src/frontmap/astroparse.py:43` (`frontmatter_script`), `:38` (`available`).
Jumeau de `tsparse` pour Astro : charge `get_parser("astro")` depuis `tree-sitter-language-pack` (extra
`[astro]`, lazy, dégradation gracieuse → None si absent). `frontmatter_script` renvoie le **texte** du
`frontmatter_js_block` (le TS entre les `---`, fences exclues) que l'appelant re-parse via `tsparse`. La
grammaire astro laisse ce bloc opaque : elle sert à le délimiter, pas à parser le TS.

## TanstackRouter — routes code-based

`src/frontmap/adapters/router_tanstack.py:102` (classe) ; `_route_calls` `:65`, `_full_path` `:87`.
Parse `createRoute({path, component, getParentRoute})` (+ `createRootRoute`) via tree-sitter :
`_route_calls` collecte les déclarations, `_full_path` chaîne les parents (protégé contre les cycles par
`stack`). `signals` = `[]` (pas de limite connue). Vide sans tree-sitter.

## ReactRouter — routes JSX (limite dynamique signalée)

`src/frontmap/adapters/router_react.py:96` (classe) ; `_collect` `:107`.
Extrait les `<Route path=… element={<X/>}>` **littéraux**, chaîne par imbrication JSX. **Limite assumée
et SIGNALÉE** : la génération dynamique (`SECTIONS.map(s => <Route/>)`, path non littéral) n'est pas
résolue — ce serait de l'analyse de flot spécifique au projet. `_collect` positionne `dynamic=True` sur
ce motif ; `signals` remonte alors « routes dynamiques non résolues » → **jamais de faux-complet**.

## tsx_component.detail() — le détail riche d'un composant

`src/frontmap/adapters/tsx_component.py:163` · appelé par `barrel`/`dir-scan`. Entrées : `root, tsx_rel,
name`. Sortie `{props, variants, defaults, lead, line}` (vide sans TS / fichier absent). Ce que code-map ne
modélise pas : props (`interface <Name>Props` OU `type Props`), **variants** (props dont le type est une
union de littéraux nommée), **defaults** (signature destructurée), **lead** (JSDoc). Deux fonctions **partagées
et réutilisées par Astro** (invariant non-duplication) : `props_and_variants` `:145` (props + variantes d'une
AST TS) et `defaults_from_text` `:139` (défauts `k = 'v'` d'un texte de params/pattern). Best-effort : props
inline anonymes non modélisées.

## astro_component.detail() — le détail via injection astro→TS

`src/frontmap/adapters/astro_component.py:39` · appelé par `AstroPrimitives.extract_primitives`. Extrait le
frontmatter (`astroparse`), le re-parse en TS (`tsparse`), **réutilise** `tsx_component.props_and_variants`
pour props/variants (même syntaxe `interface *Props` + unions nommées), et `_astro_defaults` pour les defaults
issus de `const { … } = Astro.props` (destructuring top-level, pas des params d'une fonction). Vide si l'une
des grammaires est absente ou s'il n'y a pas de frontmatter.

## Zones non détaillées

- Helpers d'AST (`_opening`, `_attrs`, `_elem_name`, `_iter_decls`, `_first_object`, `_parse_route_object`,
  `_object_props`, `_union_types`, `_component`, `_defaults`, `_astro_defaults`…) : mécanique tree-sitter
  interne — lisible au fil du code, pas une API porteuse.
