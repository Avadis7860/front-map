# adapters — runbook (le cœur générique-par-adaptateur)

`src/frontmap/adapters/` — là où code-map varie par **langage**, front-map varie par **convention** sur
DEUX axes orthogonaux : le *router* (comment les routes sont déclarées) et les *primitives* (comment le
catalogue DS est exposé). Chaque axe a son `Protocol` (schéma de sortie **figé**) ; un projet compose un
adaptateur de chaque, auto-détecté ou forcé. Contrat best-effort commun : `[]`/`set()` si source absente
ou tree-sitter manquant — **jamais d'exception**.

## resolve_router() / resolve_primitives() — choisir l'adaptateur

`src/frontmap/adapters/__init__.py:51` (router), `:56` (primitives) · appelés par `build`, `query`.
Entrées : `root, cfg`. Honorent l'override `.frontmap.toml` (`cfg.router_flavor`/`primitives_source`)
sinon délèguent à `detect_*`. Retournent l'instance depuis le registre (`router_registry` /
`primitives_registry`), avec fallback sûr (`TanstackRouter` / `BarrelPrimitives`). Point d'entrée de
toute la généricité : le reste du code parle aux Protocols, jamais à une convention en dur.

## detect_router() / detect_primitives() — auto-détection par le code

`src/frontmap/adapters/__init__.py:30` (router), `:42` (primitives) · appelés par `resolve_*` et `detect`.
`detect_router` sniffe les imports du `router_file` (`@tanstack/react-router` → `tanstack` ;
`react-router` → `react-router` ; défaut `tanstack`). `detect_primitives` : `barrel` si le barrel
existe, sinon `dir-scan` si le dossier a des `.tsx`, sinon `barrel`. La convention retenue est **tracée
au manifest** (build) — jamais devinée en silence.

## detect() — conventions retenues + disponibilité

`src/frontmap/adapters/__init__.py:61` · appelé par `cli._cmd_detect`.
Renvoie `{router, router_available, primitives, primitives_available}` — ce que le verbe `frontmap
detect` expose pour diagnostiquer un repo cible.

## RouterAdapter / PrimitivesAdapter — les Protocols (schéma figé)

`src/frontmap/adapters/base.py:48` (router), `:63` (primitives) ; rows `RouteRow` `:21`, `PrimitiveRow`
`:35`.
Les Protocols que tout adaptateur remplit. `RouterAdapter` : `available`, `extract_routes` (remplit
`RouteRow`), `referenced_files`, `signals` (limites connues). `PrimitivesAdapter` : `primitive_names`
(**contrat pivot** — regex, sans tree-sitter → `usage` marche sans `[ts]`), `consumed_primitives`
(encapsule comment CETTE convention importe une primitive), `ui_dir`, `extract_primitives`,
`missing_files`, `available`. `RouteRow`/`PrimitiveRow` sont les schémas JSONL figés (comme le `Symbol`
de code-map) : les adaptateurs les remplissent, les consommateurs ne cassent jamais.

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
fichier). Convention du web aggregator (react-router).

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

`src/frontmap/adapters/tsx_component.py:149` · appelé par les deux adaptateurs primitives.
Entrées : `root, tsx_rel, name`. Sortie `{props, variants, defaults, lead, line}` (vide sans TS /
fichier absent). Ce que code-map ne modélise pas : props (`interface <Name>Props` OU `type Props`),
**variants** (props dont le type est une union de littéraux, `_union_types`), **defaults** (signature
destructurée), **lead** (JSDoc). Best-effort : props inline anonymes non modélisées.

## Zones non détaillées

- Helpers d'AST (`_opening`, `_attrs`, `_elem_name`, `_iter_decls`, `_first_object`, `_parse_route_object`,
  `_object_props`, `_union_types`, `_component`, `_defaults`…) : mécanique tree-sitter interne — lisible
  au fil du code, pas une API porteuse.
