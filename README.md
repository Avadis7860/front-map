# front-map

> Index **design-system déterministe et interrogeable par un agent** (tokens · primitives · routes)
> — pour ancrer la génération d'UI sur un index plutôt que sur du code écrit en aveugle.

**Statut : privé · v1.** Outil **autonome**, sans service ni réseau : un CLI déterministe qui lit le
`web/` d'un projet et écrit trois index JSONL. Conçu pour être **injecté dans chaque projet géré** par le
[`cockpit`](../cockpit) — un worker IA (ou un agent UX-critic) interroge la vérité du design-system **réel**
avant d'écrire une vue, au lieu de réinventer un bouton ou de coder une couleur en dur.

## Pourquoi un outil séparé de [`code-map`](../code-map)

`code-map` répond **« où est le code / qui appelle quoi »** : il extrait des *symboles* bruts
(`class/function/type/const`) et le graphe d'imports. Pour lui, `Button` n'est qu'un `kind:function`
anonyme — il **ne modélise pas** la sémantique du design-system. `front-map` répond **« quelle primitive /
quel token / quelle route pour X »** : il modélise ce que code-map ne fait pas.

Frontière : front-map **vendorise le moteur *public* `tree-sitter`** (même extra optionnel que code-map)
et une copie du socle stdlib `core/` ; il **ne dépend pas** de code-map à l'exécution et **ne re-duplique
pas** son extracteur général de symboles — ses trois extracteurs sont étroits et DS-sémantiques.

## Verbes

| Verbe | Rôle |
|---|---|
| `frontmap build [--root R]` | (re)construit les 3 index, incrémental par hash |
| `frontmap tokens [--group G]` | design tokens (filtre optionnel : accent/status/surface/radius/…) |
| `frontmap primitives` | catalogue des primitives (résumé) |
| `frontmap primitive <name>` | détail d'une primitive : props, variantes, defaults |
| `frontmap routes` | arbre des routes (path → composant) |
| `frontmap where <intention>` | « quelle primitive / quel token pour X ? » (ranking lexical borné) |
| `frontmap check` | cohérence + fraîcheur de l'index |

## Les trois index

- **`tokens.jsonl`** — `{name, value, group, source_file, line}` depuis le CSS (`@theme` + `:root`).
  **CSS pur, toujours disponible** (aucune dépendance).
- **`primitives.jsonl`** — `{name, file, line, props, variants, defaults, lead}` depuis le barrel des
  primitives + chaque `.tsx`. Requiert `tree-sitter` (extra `[ts]`).
- **`routes.jsonl`** — `{var, path, full_path, component, parent, file, line}` depuis le router.
  Requiert `tree-sitter`.

## Principes

- **Cœur stdlib-pur** (tokens CSS) : installable partout, offline. Le **TSX** (via `tree-sitter`, roues
  pré-compilées) est un **extra optionnel** ; absent → dégradation gracieuse (primitives/routes vides,
  jamais d'erreur ; `check` le signale).
- **`build` écrit / `query` lit** : `frontmap build` matérialise les index ; les autres verbes ne font
  que lire. Aucune exécution lourde dans une requête.
- **Fraîcheur par hash de contenu** (jamais mtime) : index incrémental, skip idempotent si les sources
  n'ont pas bougé. Déterministe cross-OS (newlines normalisées).
- **Générique par configuration** : les trois sources se déclarent dans un
  [`.frontmap.toml`](./.frontmap.toml) à la racine du repo cible (défauts = conventions cockpit).

## Installation

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'          # dev inclut tree-sitter (primitives + routes)
frontmap build --root /chemin/vers/un/repo/front
frontmap primitive Button --root /chemin/vers/un/repo/front
```
