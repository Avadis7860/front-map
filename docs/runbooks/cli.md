# cli — runbook (la porte d'entrée `frontmap`)

`src/frontmap/cli.py` — une commande, dix sous-commandes, un `--root`, un `.frontmap.toml`. Jumeau
front de `codemap`. `build` écrit les 4 index ; les autres verbes lisent. Chaque verbe émet un dict JSON
stable (`+ engine`). Contrat de surface CLI **figé** (change un moteur, pas une signature).

## main() / build_parser() — point d'entrée et contrat de verbes

`src/frontmap/cli.py:149` (main), `:102` (build_parser).
`main(argv=None)` construit le parser, parse, délègue à `a.func(a)`. `build_parser` déclare
`prog="frontmap"` + `--version`, un parent commun `--root`, et les 10 sous-parsers : `build` (`--force`),
`tokens` (`--group`), `primitives`, `primitive <name>`, `routes`, `where <intent>` (`--top-k`),
`usage <name>`, `consumers <file>`, `detect`, `check`. **C'est ici que vit le contrat CLI** — toute
évolution de surface se lit/modifie à cet endroit.

## _resolve() — (racine, dossier d'index, config)

`src/frontmap/cli.py:29` · appelé par chaque `_cmd_*`.
Résout la racine (`roots.project_root`), `root/INDEX_DIRNAME` (`.frontmap/`), `Config.load(root)`. Point
unique de résolution du contexte.

## _cmd_* — les dispatchers (dont detect)

`src/frontmap/cli.py:40` (build) … `:88` (detect) … `:94` (check).
Chaque dispatcher : `_resolve`, import paresseux de `build`/`query`/`adapters`, appel du cœur, `_emit`.
`_cmd_detect` est le seul à taper `adapters.detect(root, cfg)` (conventions auto-détectées, sans index).
**Codes retour** : la plupart → 0 ; `check` → `0 si res["ok"] else 1` (statut exploitable en CI).

## _emit() — sérialisation

`src/frontmap/cli.py:35` · `print(json.dumps(..., ensure_ascii=False, indent=2))` puis `return 0`.
Source unique du format de sortie.

## Zones non détaillées

- Imports paresseux dans chaque `_cmd_*` : détail de démarrage. Le modèle du CLI : `docs/architecture.md`.
