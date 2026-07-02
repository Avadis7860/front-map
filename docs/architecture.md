# Architecture — front-map

## But

Modéliser le **design-system réel** d'un projet front en un index **déterministe et interrogeable par un
agent**, pour que la génération d'UI s'ancre sur la vérité (« quelle primitive existe pour X ? quel token
de couleur ? quelle route rend cette vue ? ») plutôt que sur du code écrit en aveugle.

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
- **ne re-duplique PAS** l'extracteur général de symboles (`symindex`) : ses trois extracteurs sont
  **étroits et purpose-built** (tokens CSS, primitives DS, routes).

Deux outils, deux vocabulaires de requête, deux évolutions → deux repos.

## Couches

```
cli.py ──────────► build.py ──────► extractors/{tokens,primitives,routes}.py ──► *.jsonl (index)
   │                  ▲                         │
   │ (build écrit)    │ fraîcheur par hash      │ tokens : CSS pur (stdlib)
   │                  │ (frontmap.manifest.json)│ primitives/routes : tsparse.py (tree-sitter, best-effort)
   └── query.py ──────┴─────────────────────────┘  (query LIT seulement)
```

- **`build`** est la SEULE couche qui exécute les extracteurs et matérialise les index. Idempotent : si
  les hash des sources **et** la disponibilité de tree-sitter sont inchangés → skip.
- **`query`** ne fait que lire les JSONL. Aucune exécution lourde dans une requête (invariant jumeau de
  code-map `query.py`).
- **`tsparse`** centralise le parser tree-sitter (lazy, dégradation gracieuse) partagé par primitives+routes.

## Schéma des index (contrat)

- **`tokens.jsonl`** — `{name, value, group, source_file, line, lead}`. `group` ∈ `accent · status ·
  surface · radius · shadow · motion · typography · z · other`, dérivé du préfixe du nom.
- **`primitives.jsonl`** — `{name, file, line, props:[{name,type,optional}], variants:{prop:[valeurs]},
  defaults:{prop:valeur}, lead}`. `variants` = props dont le type est une union de littéraux string.
- **`routes.jsonl`** — `{var, path, full_path, component, parent, is_root, file, line}`. `full_path`
  reconstruit en chaînant les `getParentRoute`.
- **`frontmap.manifest.json`** — `{contract_version, ts_available, counts, file_hashes}`. Base de la
  fraîcheur (hash de contenu ; la signature `ts_available` invalide la réutilisation quand tree-sitter
  apparaît/disparaît).

## Détection par convention

Aucune config obligatoire : les trois sources ont des défauts calés sur les conventions cockpit
(`web/src/index.css`, `web/src/components/ui/index.ts`, `web/src/router.tsx`), surchargeables via
`.frontmap.toml` à la racine du repo cible. L'**autorité** de la liste des primitives est le **barrel**
(ses exports de valeur), pas un scan de dossier — un composant hors barrel n'est pas une primitive.

## Dégradation gracieuse

tree-sitter absent → `primitives`/`routes` vides (jamais d'exception) ; `tokens` (CSS pur) reste produit.
`check` **signale** l'absence et l'éventuelle péremption de l'index (pas de faux-vert silencieux).
