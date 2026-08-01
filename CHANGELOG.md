# Changelog

Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) · versionnage [SemVer](https://semver.org/lang/fr/).

> **Ouvert le 2026-08-01**, à partir du portage de la garde d'index-absent (`8a532b2`). Les **10 commits
> antérieurs ne sont PAS reconstruits** : les réécrire aujourd'hui de mémoire produirait de la
> reconstruction d'historique, pas de la documentation. La genèse vit dans `git log`.
>
> Pourquoi maintenant : `code-map` et `docs-map` portaient un changelog depuis leur commit de genèse,
> `front-map` non — le seul des trois. Or les constitutions des deux jumeaux imposent « on change un
> *moteur*, pas un *schéma* → sinon **bump + changelog** » ; la clause manquait ici, et le changelog avec.
> Écart relevé le 2026-08-01 (phase 5 de `ROADMAP-tooling-honesty`), désormais **mesuré** côté vault par
> `health.py::check_map_toolkit_parity`.

## [Non publié]

### Corrigé — les verbes de lecture ne mentent plus quand l'index est absent (`8a532b2`)

`tokens`/`primitives`/`routes`/`usage`/`consumers`/`where` rendaient `{"tokens": [], "count": 0}` — un
**vide trompeur**, `read_jsonl` renvoyant `[]` sur fichier absent : impossible de distinguer « pas de
token » de « pas d'index », et l'appelant retombait sur `grep`. Ils rendent désormais
`{"ok": false, "reason": "index absent — lance \`frontmap build\`"}`.

`check`, lui, portait déjà sa garde honnête — c'est ce qui a rendu l'asymétrie visible.

**Aucun changement de contrat** : `CONTRACT_VERSION` (`frontmap-index-v1`), le schéma JSONL et les
signatures CLI sont intacts ; la sortie nominale n'a pas bougé d'un champ.

### Ajouté — emprunt de l'index du répertoire principal depuis une worktree (`8a532b2`)

L'index est un dérivé gitignoré : `git worktree add` ne l'emporte pas. Or la boucle de travail impose la
worktree — donc, là où tout le travail se fait, `frontmap` répondait « rien » et l'agent lisait `web/` en
bloc, exactement ce que la règle anti-archéologie interdit.

`roots.main_worktree_root()` résout la racine du répertoire de travail principal en **stdlib pure**
(gitfile `.git` + `commondir`, **aucun sous-processus `git`**, fail-soft intégral : toute déviation rend
`None`, jamais une racine devinée). `cli._resolve(borrow=True)` s'en sert pour les verbes de **lecture**.

**`build` n'emprunte jamais** (`borrow=False`) : il écrirait l'index de la feature dans le répertoire
principal, corrompant en silence celui de `dev`. **`check` non plus** — et pour une autre raison : il
diagnostique l'index **local**, répondre avec celui du principal transformerait « tu n'as pas d'index ici »
en verdict vert sur l'index d'un autre.

**Fraîcheur annoncée sur stderr**, jamais dans l'enveloppe JSON : l'index emprunté ignore le code de la
worktree, et l'invariant maison est « jamais de cap silencieux » — mais l'enveloppe est un contrat figé
dont tout ajout de champ imposerait un rebuild chez les consommateurs.
