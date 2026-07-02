# front-map

> Index **design-system déterministe et interrogeable par un agent** (tokens · primitives · routes · usage)
> — pour ancrer la génération d'UI sur un index plutôt que sur du code écrit en aveugle.

**Statut : privé · v1.** Outil **autonome**, sans service ni réseau : un CLI déterministe qui lit le
`web/` d'un projet et écrit quatre index JSONL. Conçu pour être **injecté dans chaque projet géré** par le
[`cockpit`](../cockpit) — un worker IA (ou un agent UX-critic) interroge la vérité du design-system **réel**
avant d'écrire une vue, au lieu de réinventer un bouton ou de coder une couleur en dur.

## Pourquoi un outil séparé de [`code-map`](../code-map)

`code-map` répond **« où est le code / qui appelle quoi »** : il extrait des *symboles* bruts
(`class/function/type/const`) et le graphe d'imports. Pour lui, `Button` n'est qu'un `kind:function`
anonyme — il **ne modélise pas** la sémantique du design-system. `front-map` répond **« quelle primitive /
quel token / quelle route pour X »** : il modélise ce que code-map ne fait pas.

Frontière : front-map **vendorise le moteur *public* `tree-sitter`** (même extra optionnel que code-map)
et une copie du socle stdlib `core/` ; il **ne dépend pas** de code-map à l'exécution et **ne re-duplique
pas** son extracteur général de symboles — ses quatre extracteurs sont étroits et DS-sémantiques.

**Générique par convention (comme code-map est multi-langage).** Là où code-map varie par *langage* via
des *engines*, front-map varie par *convention* via des **adaptateurs** sur deux axes orthogonaux :
- **router** : `tanstack` (TanStack code-based `createRoute`) · `react-router` (JSX `<Route>`) ;
- **primitives** : `barrel` (`components/ui/index.ts` ré-exporte) · `dir-scan` (un `.tsx` par primitive, sans barrel).

La convention est **auto-détectée** (sniff des imports du router, présence d'un barrel) — ou forcée dans
`.frontmap.toml`. Un axe inconnu dégrade gracieusement et le signale ; ajouter une convention = un nouvel
adaptateur dans le registre (`src/frontmap/adapters/`), rien d'autre ne bouge.

## Verbes

| Verbe | Rôle |
|---|---|
| `frontmap build [--root R]` | (re)construit les 4 index, incrémental par hash |
| `frontmap tokens [--group G]` | design tokens (filtre optionnel : accent/status/surface/radius/…) |
| `frontmap primitives` | catalogue des primitives (résumé) |
| `frontmap primitive <name>` | détail d'une primitive : props, variantes, defaults |
| `frontmap routes` | arbre des routes (path → composant) |
| `frontmap where <intention>` | « quelle primitive / quel token pour X ? » (ranking lexical borné) |
| `frontmap usage <name>` | index **inversé** : « qui consomme cette primitive / ce token ? » |
| `frontmap consumers <file>` | ce qu'un écran consomme : primitives + tokens + route |
| `frontmap detect` | conventions auto-détectées du repo (router / primitives) |
| `frontmap check` | cohérence + fraîcheur + signaux (routes dynamiques, primitives jamais consommées) |

## Les quatre index

- **`tokens.jsonl`** — `{name, value, group, source_file, line}` depuis le CSS (`@theme` + `:root`).
  **CSS pur, toujours disponible** (aucune dépendance).
- **`primitives.jsonl`** — `{name, file, line, props, variants, defaults, lead}` depuis l'adaptateur
  primitives résolu (barrel **ou** dir-scan). Le catalogue **riche** requiert `tree-sitter` (extra `[ts]`) ;
  les **noms** (contrat pivot pour `usage`) sont extraits sans (regex/filesystem).
- **`routes.jsonl`** — `{var, path, full_path, component, parent, is_root, file, line}` depuis l'adaptateur
  router résolu (tanstack **ou** react-router). Requiert `tree-sitter`.
- **`usage.jsonl`** — `{consumer, kind, primitives, tokens, route}` : index **inverse** de consommation
  (qui importe quelle primitive, quels tokens littéraux, sous quelle route). **Pur-Python** — marche sans
  `tree-sitter` (seul le lien `route` se dégrade à `null`).

## Principes

- **Cœur stdlib-pur** (tokens CSS) : installable partout, offline. Le **TSX** (via `tree-sitter`, roues
  pré-compilées) est un **extra optionnel** ; absent → dégradation gracieuse (primitives/routes vides,
  jamais d'erreur ; `check` le signale).
- **`build` écrit / `query` lit** : `frontmap build` matérialise les index ; les autres verbes ne font
  que lire. Aucune exécution lourde dans une requête.
- **Fraîcheur par hash de contenu** (jamais mtime) : index incrémental, skip idempotent si les sources
  n'ont pas bougé. Déterministe cross-OS (newlines normalisées).
- **Générique par convention** : sources + axes (router / primitives) se déclarent dans un
  [`.frontmap.toml`](./.frontmap.toml) à la racine du repo cible (défauts = conventions cockpit,
  convention auto-détectée). Prouvé sur deux projets réels aux conventions opposées (cockpit TanStack+barrel,
  aggregator react-router+dir-scan).

## Installation

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'          # dev inclut tree-sitter (primitives + routes)
frontmap build --root /chemin/vers/un/repo/front
frontmap primitive Button --root /chemin/vers/un/repo/front
```
