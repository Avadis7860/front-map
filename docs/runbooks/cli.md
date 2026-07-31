# cli — runbook (la porte d'entrée `frontmap`)

`src/frontmap/cli.py` — une commande, dix sous-commandes, un `--root`, un `.frontmap.toml`. Jumeau
front de `codemap`. `build` écrit les 4 index ; les autres verbes lisent. Chaque verbe émet un dict JSON
stable (`+ engine`). Contrat de surface CLI **figé** (change un moteur, pas une signature).

## main() / build_parser() — point d'entrée, contrat de verbes, garde d'index

`src/frontmap/cli.py:205` (main), `:155` (build_parser).
`main(argv=None)` construit le parser, parse, délègue à `a.func(a)`. `build_parser` déclare
`prog="frontmap"` + `--version`, un parent commun `--root`, et les 10 sous-parsers : `build` (`--force`),
`tokens` (`--group`), `primitives`, `primitive <name>`, `routes`, `where <intent>` (`--top-k`),
`usage <name>`, `consumers <file>`, `detect`, `check`. **C'est ici que vit le contrat CLI** — toute
évolution de surface se lit/modifie à cet endroit.

`main()` fait **deux** choses avant de déléguer :

1. remet `_borrow_warned` à zéro — l'avertissement d'emprunt est un état **par invocation**, pas par
   processus (`main()` est rappelé en test, en cours de processus) ;
2. applique la **garde d'index-absent** aux verbes marqués `needs_index=True` (les 7 verbes de lecture).
   Sans elle, ils rendaient un vide **trompeur** — `{"tokens": [], "count": 0}`, rc 0 : impossible de
   distinguer « ce repo n'a aucun token » de « personne n'a bâti l'index ». Désormais
   `{"ok": false, "reason": "index absent — lance `frontmap build`"}`, **rc inchangé**.
   `build` (il bâtit), `detect` (il lit les sources) et `check` (il diagnostique l'absence lui-même,
   avec ses champs typés) ne portent PAS le marqueur.

## _resolve() — (racine, dossier d'index, config) + emprunt en worktree

`src/frontmap/cli.py:56` · appelé par chaque `_cmd_*`.
Résout la racine (`roots.project_root`), `root/INDEX_DIRNAME` (`.frontmap/`), `Config.load(root)`. Point
unique de résolution du contexte.

`borrow=True` (les 7 verbes de **lecture** + la garde de `main()`) : dans une **worktree liée sans index
propre**, on lit celui du répertoire de travail principal. Motif : les index dérivés sont gitignorés, donc
`git worktree add` ne les emporte pas — et la worktree est justement l'endroit où tout le travail se fait.
Trois garde-fous **porteurs** :

- **Les verbes qui écrivent n'empruntent jamais.** `build` écrirait l'index de la feature dans le
  répertoire principal (corruption silencieuse de celui de `dev`). Le critère est « ce verbe écrit-il
  dans `index_dir` ? », **jamais son nom** — dans code-map, `map` est le piège (il appelle `symbols.build`).
- **`check` n'emprunte pas non plus.** Il diagnostique l'index **local** ; répondre avec celui du principal
  transformerait « tu n'as pas d'index ici » en verdict vert sur l'index d'un autre.
- **Fraîcheur annoncée sur stderr, jamais dans le JSON** (`_warn_borrow`, `:40`) : l'index emprunté ignore
  le code de la worktree. Le stdout consommé par un agent n'a pas bougé d'un octet.

Rien à emprunter (le principal n'a pas d'index non plus) ⇒ la garde d'index-absent reprend la main : un
silence honnête, jamais un mensonge. Résolution du répertoire principal : `roots.main_worktree_root`
(voir `docs/runbooks/core.md`).

## _cmd_* — les dispatchers (dont detect)

`src/frontmap/cli.py:86` (build) … `:137` (detect) … `:143` (check).
Chaque dispatcher : `_resolve`, import paresseux de `build`/`query`/`adapters`, appel du cœur, `_emit`.
`_cmd_detect` est le seul à taper `adapters.detect(root, cfg)` (conventions auto-détectées, sans index).
**Codes retour** : la plupart → 0 ; `check` → `0 si res["ok"] else 1` (statut exploitable en CI).

## _emit() / _sentinel() — sérialisation et marqueur de build

`src/frontmap/cli.py:81` · `print(json.dumps(..., ensure_ascii=False, indent=2))` puis `return 0`.
Source unique du format de sortie.

`_sentinel()` (`:32`) rend `build.MANIFEST_NAME` — le marqueur « un build a réellement tourné », celui-là
même que `check` interroge. Import **paresseux** (charger `frontmap.build` tire les adaptateurs et
tree-sitter ; `--help` n'a pas à les payer) et **sans constante dupliquée**, donc rien qui puisse dériver.

## Zones non détaillées

- Imports paresseux dans chaque `_cmd_*` : détail de démarrage. Le modèle du CLI : `docs/architecture.md`.
