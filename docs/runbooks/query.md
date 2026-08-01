# query — runbook (les verbes de lecture du DS queryable)

`src/frontmap/query.py` — navigation **lecture seule** : consomme les 4 index, n'exécute aucun
extracteur. Chaque verbe renvoie un dict stable + `"engine": "frontmap-v1"`. L'index doit exister
(`frontmap build`). C'est la surface anti-archéologie front : interroger avant de grep le web.

## tokens() — les design tokens (filtre optionnel par groupe)

`src/frontmap/query.py:35` · appelé par `cli._cmd_tokens`.
Entrées : `index_dir, group=None`. Lit `tokens.jsonl`, filtre sur `group` si fourni
(`accent|status|surface|radius|shadow|motion|typography|z|other`). Sortie `{tokens, count, engine}`.

## primitives() — catalogue résumé

`src/frontmap/query.py:42` · appelé par `cli._cmd_primitives`.
Résumé de `primitives.jsonl` : `{name, lead, variants triés, n_props, file}` par primitive. Vue
d'ensemble bon marché du design-system.

## primitive() — détail d'une primitive

`src/frontmap/query.py:49` · appelé par `cli._cmd_primitive`.
Entrées : `index_dir, name` (**insensible à la casse**). Renvoie l'enregistrement complet (props,
variants, defaults, lead, file, line) ou `{error, available}` avec la liste des noms connus.

## routes() — l'arbre des routes

`src/frontmap/query.py:58` · appelé par `cli._cmd_routes`.
Renvoie `routes.jsonl` tel quel (`{routes, count, engine}`) — les `RouteRow` chaînés par `full_path`.

## where() — quelle primitive / quel token pour une intention

`src/frontmap/query.py:63` · appelé par `cli._cmd_where`.
Entrées : `index_dir, intent, top_k=5`. Tokenise l'intention, score chaque primitive (nom + lead +
valeurs de variantes + noms de props) ET chaque token (nom + valeur + groupe + lead) via `text.score`,
ne garde que `score>0`, trie décroissant. Sortie `{results, engine}` où chaque hit porte `kind`
(`primitive`|`token`). Le verbe d'orientation « quel élément DS pour X ».

## usage() — index INVERSE : qui consomme `name`

`src/frontmap/query.py:87` · appelé par `cli._cmd_usage`.
Entrées : `index_dir, name`. Cherche dans `usage.jsonl` les consommateurs où `name` apparaît comme
primitive (insensible à la casse) ou token (exact). Sortie `{target, as_primitive, as_token, count}`.
Répond « si je change ce token/cette primitive, qui casse ».

## consumers() — ce qu'un écran consomme

`src/frontmap/query.py:97` · appelé par `cli._cmd_consumers`.
Entrées : `index_dir, file` (chemin rel exact, suffixe `/file`, ou basename). Renvoie l'enregistrement
`usage` du fichier (primitives + tokens + route) ou `{error, available}`.

## freshness() — l'état de fraîcheur BRUT (sortie interne, source unique)

`src/frontmap/query.py:109`.
Re-hache les sources et compare au manifest. Sépare ce que `check` aplatit en un seul booléen `fresh`,
parce que les causes ne coûtent pas la même chose au lecteur : `unindexed` = le fichier est **absent** de
toute réponse (c'est ainsi qu'une primitive livrée reste invisible au catalogue), `drifted` = ce qui est
servi pour lui est **faux**, `removed` = l'index sert une primitive d'un fichier disparu ; `ts_changed` et
`conventions_changed` n'accusent aucun fichier — l'index entier repose sur une autre hypothèse.
Rend `{ok, files, unindexed, drifted, removed, ts_changed, conventions_changed}`, ou `{ok:false, reason}`
si le manifest manque (**sans** clé `files` — le discriminant des appelants).

Deux consommateurs, un seul calcul : `check()` en est le **formateur** (sortie inchangée, contrat figé) et
`cli._warn_stale` en exploite le détail par cause. Un second calculateur de fraîcheur dériverait du
premier, et l'écart entre les deux deviendrait le prochain faux-vert.

## check() — cohérence + fraîcheur (SIGNALE, ne juge pas)

`src/frontmap/query.py:147` · appelé par `cli._cmd_check`.
Formateur de `freshness()` ; vérifie en plus tree-sitter présent, convention résolue et source
de primitives complète (`prim.available` / `prim.missing_files`). `findings` invalident `ok` (index
périmé, source absente) ; **`signals`** n'invalident PAS (routes dynamiques via `router.signals`,
primitives jamais consommées) — front-map **signale**, le verdict revient au futur agent UX.
Un troisième registre, **`primitives_status`**, dit la qualité de ce qu'on sait de la source de primitives,
indépendamment de sa fraîcheur : `verified` (source présente ET grammaire de détail chargeable → catalogue
vérifié), `names_only` (source présente mais grammaire absente → les noms sont connus, le détail est vide,
et ce n'est donc **pas** un vert), `unavailable` (source introuvable). C'est la garde anti faux-vert de la
généricité par convention : une source `.astro` sans l'extra `[astro]` ne doit pas se lire comme un
catalogue vérifié. Sortie
`{ok, ts_available, fresh, conventions, primitives_status, counts, findings, signals, engine}`.

## Zones non détaillées

- Helpers `_load`, `_consumer_ref` : triviaux. Le scoring : voir `runbooks/core.md` (`text.score`).
