# Architecture — front-map

## But

Modéliser le **design-system réel** d'un projet front en un index **déterministe et interrogeable par un
agent**, pour que la génération d'UI s'ancre sur la vérité (« quelle primitive existe pour X ? quel token
de couleur ? quelle route rend cette vue ? **qui consomme cette primitive ?** ») plutôt que sur du code
écrit en aveugle.

## Frontière avec code-map (verrouillée)

code-map répond « **où est le code / qui appelle quoi** » : il extrait des *symboles* bruts
(`class/function/type/const`, schéma **gelé**) + le graphe d'imports. Il ne modélise **pas** la sémantique
du design-system — pour lui `Button` est un `kind:function` anonyme, un token n'est qu'un `const`, un
`createRoute` un appel.

front-map répond « **quelle primitive / quel token / quelle route pour X** ». Il modélise cette couche
sémantique que code-map ne fait pas. Il :

- **vendorise** le moteur *public* `tree-sitter` (même extra `[ts]` que code-map) et une **copie** du socle
  stdlib `core/` (`hashing`, `jsonl`, `roots`, `text`) ;
- **ne dépend PAS** de code-map à l'exécution, ne lit pas son index ;
- **ne re-duplique PAS** l'extracteur général de symboles (`symindex`) : ses quatre extracteurs sont
  **étroits et purpose-built** (tokens CSS, primitives DS, routes, usage).

La couche **`usage`** (« qui consomme quoi ») illustre la frontière : ce n'est **pas** un graphe d'imports
général (ça, c'est code-map), mais un index **inverse** sur le vocabulaire *déjà connu de front-map* (ses
primitives, ses tokens). Elle re-parse les imports en interne (regex, comme le barrel) — donc pur-Python,
sans dépendre de code-map ni de tree-sitter.

Deux outils, deux vocabulaires de requête, deux évolutions → deux repos.

**Générique par convention (comme code-map est multi-langage).** code-map varie par *langage* via des
*engines* ; front-map varie par *convention* via des **adaptateurs** (`src/frontmap/adapters/`) sur deux
axes ORTHOGONAUX — **router** (`tanstack` | `react-router`) et **primitives** (`barrel` | `dir-scan` | `astro`).
Même patron que `engines/` de code-map : un `Protocol` par axe (`base.py`) + un schéma de ligne JSONL
**figé** que les adaptateurs remplissent + un registre (`__init__.py`) + une détection par signatures de
fichiers. La convention est auto-détectée ou forcée dans `.frontmap.toml`. Ajouter une convention = un
adaptateur de plus, rien d'autre ne bouge.

## Couches

```
cli.py ─► build.py ─► adapters.resolve_{router,primitives}(cfg) ─┐
   │          ▲            (auto-détection ou override)           ├─► *.jsonl (index)
   │(écrit)   │ fraîcheur   extractors/tokens.py (CSS pur)        │
   │          │ par hash    extractors/usage.py (regex, délègue   │
   └─query.py─┘ (manifest)   la conso à l'adaptateur primitives)  ┘   (query LIT seulement)

adapters/  base.py (Protocols + schéma figé) · __init__.py (registres + detect/resolve)
           router_{tanstack,react}.py · primitives_{barrel,dirscan,astro}.py
           tsx_component.py (détail TSX partagé) · astro_component.py (détail frontmatter, réutilise tsx_component)
```

- **`build`** résout les adaptateurs (par convention), exécute les extracteurs, matérialise les index.
  Idempotent : skip si hash des sources **et** dispo tree-sitter **et** convention retenue inchangés.
- **`query`** ne fait que lire les JSONL. Aucune exécution lourde dans une requête (invariant code-map).
- **`tsparse`** centralise le parser tree-sitter TS/TSX (lazy, dégradation gracieuse), partagé par les
  adaptateurs. **`astroparse`** fait de même pour la grammaire astro (délimite le frontmatter, extra `[astro]`).

## Schéma des index (contrat)

- **`tokens.jsonl`** — `{name, value, group, source_file, line, lead}`. `group` ∈ `accent · status ·
  surface · radius · shadow · motion · typography · z · other`, dérivé du préfixe du nom.
- **`primitives.jsonl`** — `{name, file, line, props:[{name,type,optional}], variants:{prop:[valeurs]},
  defaults:{prop:valeur}, lead}`. `variants` = props dont le type est une union de littéraux string.
- **`routes.jsonl`** — `{var, path, full_path, component, parent, is_root, file, line}`. Rempli par
  l'adaptateur router (tanstack : chaînage `getParentRoute` ; react-router : imbrication JSX `<Route>`).
- **`usage.jsonl`** — `{consumer, kind:page|component, primitives:[…], tokens:[…], route}`. Un fichier par
  consommateur du DS (fichier sans aucune primitive/token connu → omis). `primitives` = primitives connues
  consommées, la détection étant **déléguée à l'adaptateur** (barrel : import nommé ; dir-scan : import par
  défaut d'un fichier) ; `tokens` = tokens connus référencés littéralement (`var(--…)`, best-effort — pas la
  forme utilitaire Tailwind) ; `route` = `full_path` si le fichier est le composant d'une route, sinon `null`.
- **`frontmap.manifest.json`** — `{contract_version, ts_available, conventions:{router,primitives}, counts,
  file_hashes}`. Base de la fraîcheur (hash de contenu ; les signatures `ts_available` **et** `conventions`
  invalident la réutilisation quand tree-sitter ou la convention retenue changent).

## Détection par convention (deux axes)

Aucune config obligatoire : les sources ont des défauts cockpit, et la **convention** de chaque axe est
auto-détectée (`.frontmap.toml` peut forcer via `[conventions] router / primitives`) :
- **router** — sniff des imports du `router_file` : `@tanstack/react-router` → `tanstack` ; `react-router`
  → `react-router` ; défaut `tanstack`.
- **primitives** — `barrel` si `primitives_barrel` existe ; sinon `dir-scan` si `primitives_dir` contient des
  `.tsx` ; sinon `astro` si `primitives_dir` contient des `.astro` ; défaut `barrel`. En `barrel` l'autorité
  est le barrel (ses exports de valeur) ; en `dir-scan`/`astro` c'est le dossier (un fichier = une primitive,
  nom = stem du fichier). L'ordre garde barrel/dir-scan prioritaires : `astro` n'est retenu que sur un dossier
  réellement Astro, donc **aucun projet TSX existant ne change de convention**.

En `astro`, le détail (props/variants/defaults) vit dans le **frontmatter** (`---`) du composant : une
`interface Props`, des unions de littéraux nommées (variantes), un `const { … } = Astro.props` (defaults). La
grammaire astro (`tree-sitter-language-pack`, extra `[astro]`) **délimite** ce bloc mais le laisse opaque ; on
le re-parse avec la grammaire TS (`tsparse`, extra `[ts]`) et on **réutilise** l'extraction TSX
(`tsx_component.props_and_variants`) — c'est une *injection de langage* faite à la main. Les NOMS restent
filesystem (stem), donc connus sans aucun extra.

La convention retenue est **tracée au manifest** et exposée par `frontmap detect` / `frontmap check` — jamais
devinée en silence. `check` porte un statut typé **`primitives_status`** (`verified` | `names_only` |
`unavailable`) : une source présente mais dont la grammaire de détail est absente (ex. `.astro` sans `[astro]`)
est `names_only` → **rouge honnête**, jamais faux-vert ni confondu avec « source introuvable ». Prouvé sur
trois projets réels opposés (cockpit TanStack+barrel, aggregator react-router+dir-scan, vitrine Astro).

## Dégradation gracieuse

tree-sitter absent → catalogue `primitives`/`routes` vide (jamais d'exception) ; `tokens` (CSS pur) reste
produit. `usage` reste produit lui aussi (pur-Python : **noms** de primitives via l'adaptateur — regex/
filesystem, sans tree-sitter — tokens via scan littéral) — seul son `route` se dégrade à `null`. `check`
**signale** (sans invalider `ok` pour les signaux) : absence de tree-sitter, index périmé, **routes
dynamiques** non résolues par l'adaptateur router (`.map`), primitives déclarées mais **jamais consommées**.
front-map *signale*, il ne juge pas (le verdict est l'affaire du futur agent UX-critic).
