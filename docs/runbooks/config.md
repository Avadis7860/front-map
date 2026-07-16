# config — runbook (la config déclarative du repo cible)

`src/frontmap/config.py` — charge `.frontmap.toml` à la racine du repo indexé. Jumeau de code-map.
Absent → défauts génériques + auto-détection. `tomllib` stdlib → **zéro dépendance**. `INDEX_DIRNAME =
".frontmap"` : seul lieu où vit le chemin des index dérivés. **Invariant : rien de spécifique-projet en
dur** — tout passe par la config.

## Config — le contrat de config résolu

`src/frontmap/config.py:21` · consommé par `build`, `query`, `adapters`, `cli._resolve`.
Dataclass **frozen**. Sources : `tokens_file`, `primitives_barrel`, `primitives_dir`, `router_file`,
`web_root`, `import_alias` (défauts = conventions cockpit : `web/` Vite+React+TanStack+barrel). **Axes de
convention** : `router_flavor` (`auto|tanstack|react-router`) et `primitives_source` (`auto|barrel|
dir-scan`) — `"auto"` → détection depuis le code (`adapters.detect_*`) ; un `.frontmap.toml` peut forcer.
Immuable → une config chargée ne dérive pas.

## Config.load() — .frontmap.toml → Config (ou défauts)

`src/frontmap/config.py:37` · appelé par `cli._resolve`.
Entrées : `root`. Absent → `Config()`. Sinon parse le TOML, lit les tables `[sources]` et `[conventions]`,
surcharge champ par champ (défaut si clé absente). Point d'entrée unique de la configuration ; les flags
CLI la complètent en amont via `roots.project_root`.

## Zones non détaillées

- Constantes `CONFIG_FILENAME`, `INDEX_DIRNAME`, `ROUTER_FLAVORS`, `PRIMITIVES_SOURCES` : lisibles inline.
- Le *pourquoi* des deux axes de convention : `runbooks/adapters.md` + `docs/architecture.md`.
