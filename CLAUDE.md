# CLAUDE.md — front-map (index design-system déterministe)

> Lu au début de **chaque** session opérant dans ce repo. Persona `tool-builder` active. Cadre
> **verrouillé** ci-dessous — ne pas re-débattre ; livrer. Outil du framework *cockpit* (repos frères :
> `cockpit`, `code-map`, `mcp-catalogs`).

## 1. Mission

Un **CLI déterministe** qui transforme le `web/` d'un projet en index interrogeables — **tokens**,
**primitives**, **routes** — pour répondre à « quelle primitive / quel token / quelle route pour X »
**sans coder l'UI en aveugle**. Injecté dans chaque projet géré par le cockpit : un worker (ou un agent
UX-critic) interroge le design-system **réel** avant d'écrire une vue.

**Succès (binaire)** : `pip install -e '.[ts]'` puis `frontmap build --root <repo front>` →
`primitive Button` sort ses variantes/props, `tokens accent` les tokens accent, `routes` l'arbre, `where`
classe la bonne primitive ; deux builds sur sources inchangées → **skip idempotent** (fraîcheur par hash).

## 2. Framework VERROUILLÉ (ne pas re-choisir)

- **Python ≥ 3.11, cœur stdlib-pur** (`re`, `argparse`, `tomllib`, `pathlib`, `hashlib`) — **zéro
  dépendance obligatoire**. L'extraction **TSX** (primitives + routes) = **extra optionnel** `[ts]`
  (tree-sitter, roues pré-compilées) à **dégradation gracieuse** (absent → vides, jamais une erreur ; les
  **tokens CSS** restent, eux, toujours disponibles).
- **Jumeau de code-map, pas un fork** : on **vendorise** le moteur public tree-sitter + le socle stdlib
  `core/` (copie) ; on **ne dépend PAS** de code-map à l'exécution et on **ne re-duplique PAS** son
  extracteur général de symboles. front-map modélise ce que code-map ne modélise pas (la sémantique DS).
- **Package installable** (src-layout, hatchling), **un CLI unifié** `frontmap`. `build` écrit / `query` lit.
- **Pas de serveur, pas de MCP** : un outil local déterministe. Fichiers JSONL + CLI.
- **Générique par configuration** (`.frontmap.toml`), **aucun chemin en dur** (défauts = conventions cockpit).
- **Multi-OS** : chemins POSIX, `eol=lf`, hash newline-universel → index déterministe.

## 3. Comment travailler ici

- **Les docs sont la spec** : lis `docs/architecture.md` **avant** de coder. Le schéma des 3 index JSONL
  est un **contrat** — on change un *extracteur*, pas un *schéma* (sinon : bump + note).
- **Anti-archéologie** : quand `frontmap` est fonctionnel sur un repo, interroge-le
  (`primitives/tokens/routes/where`) au lieu de grep le front.
- **Anti-boucle** : avant une API tree-sitter non triviale, le code de `tsparse.py` et
  `code-map/engines/typescript_ts.py` sont la référence — n'invente pas de type de nœud.
- **Qualité = gate** : `ruff` + `mypy` + `pytest` **verts** avant tout commit. Le déterminisme se **teste**
  (skip idempotent). Fixtures minuscules, mini `web/` d'échantillon (jamais un vrai fichier d'un projet réel).
- **Git** : branche `feature/<sujet>` depuis `dev`, jamais de commit direct sur `main`/`dev`.

## 4. Anti-patterns (à ne jamais faire)

- ❌ Ajouter une **dépendance obligatoire** au cœur (il reste stdlib-pur ; tree-sitter = extra optionnel).
- ❌ **Dépendre de code-map** à l'exécution, ou y re-copier son extracteur de symboles (frontière verrouillée).
- ❌ Changer un **schéma JSONL** sans bump + note (contrat inter-repos, consommé par le cockpit).
- ❌ Inventer une signature d'API « de mémoire » au lieu de lire le code / la stdlib.
- ❌ **Cap silencieux** : toute dégradation (tree-sitter absent, fichier introuvable) se **signale** (`check`).
- ❌ Juger la fraîcheur au **mtime** — toujours **par hash de contenu**.
