# front-map — la carte du design-system, interrogeable

## Ce que c'est

Un CLI **autonome, déterministe** (frère de code-map) qui lit le `web/` d'un projet et écrit quatre index
JSONL : **tokens · primitives · routes · usage**. Là où code-map répond « où est le code / qui appelle quoi »,
front-map répond « **quelle primitive / quel token / quelle route pour X** » — il modélise la *sémantique du
design-system* que code-map ne voit pas (pour lui, `Button` n'est qu'une fonction anonyme). Générique par
**convention auto-détectée** (router `tanstack`/`react-router`, primitives `barrel`/`dir-scan`) ; un axe
inconnu dégrade gracieusement et le signale.

## Pourquoi l'utiliser avec Claude

Un agent qui génère une vue **en aveugle** réinvente un bouton, code une couleur en dur, ajoute une route qui
double une existante. front-map lui donne la **vérité du design-system réel** : il interroge les primitives et
tokens **existants** avant d'écrire, au lieu de dupliquer. C'est l'ancrage de la génération d'UI — l'équivalent
de code-map pour le front, consommé aussi par un agent UX-critic.

## En bref

- `frontmap build` — (re)construit les 4 index (incrémental par hash).
- interroger **tokens / primitives / routes / usage** avant de coder une vue.
- convention auto-détectée, forçable dans `.frontmap.toml` ; extra `tree-sitter` optionnel.
