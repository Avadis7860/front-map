# .claude/ — contexte & starter pack de session (bundle `front-map`)

Rend le repo **auto-décrivant et outillé** : une session Claude ouverte ici (ou quand le repo est monté
dans un projet) démarre câblée, orientée, et gated — sans configuration manuelle.

| Élément | Rôle |
|---|---|
| [`../CLAUDE.md`](../CLAUDE.md) | Constitution **mince** : règles non négociables + **index** vers `docs/` + **outils** embarqués (le détail vit dans `docs/`, pas ici). |
| `output-styles/tool-builder.md` | Persona : outil déterministe (stdlib d'abord, schéma figé, zéro cap silencieux, adossé aux tests). |
| `skills/work-loop/` | Boucle de travail **sûre et lightweight** (worktree feature depuis `dev` → gate → `dev` ff-only → `main` promu) — **sans cockpit**. |
| `skills/quality-gate/` | Gate ruff + mypy + pytest + déterminisme/idempotence — **avant chaque commit**. |
| `skills/port-tool/` | Le workflow récurrent : porter/ajouter un module (source → correctif → module + test → gate). |
| `hooks/post-edit-check.py` | `PostToolUse` (Write\|Edit) : `py_compile` + ruff léger sur le `.py`/`.json`/`.toml` touché, non bloquant. |
| `templates/module.py.tmpl` · `templates/test_module.py.tmpl` | Scaffolds d'un module + test fixture/déterminisme. |
| `settings.json` | Câble le hook + `outputStyle` + permissions. |

## Origine (bibliothèque de bundles)

Bundle **`front-map`** dérivé de l'archétype `code-map` (« outil de dev déterministe », jumeau front),
persona `tool-builder`, stack `python-quality`. La **source canonique** est le vault
(`bundles/front-map/`) ; ici c'est l'instance qui **voyage avec le repo**. Faire évoluer le contexte
durablement = modifier le bundle côté vault **puis** re-vendorer — ne pas laisser diverger.
