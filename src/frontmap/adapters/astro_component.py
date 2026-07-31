"""astro_component — détail d'une primitive Astro (props/variants/defaults/lead), via injection astro→TS.

Un composant `.astro` porte son API dans le **frontmatter** (le bloc `---`) : une `interface Props`, des
unions de littéraux (variantes) et un destructuring `const { variant = 'x' } = Astro.props` (defaults). La
grammaire astro délimite ce bloc mais ne le parse pas ; on le re-parse donc avec la grammaire TS (`tsparse`)
et on **réutilise** l'extraction déjà écrite pour TSX (`tsx_component.props_and_variants`) — même syntaxe
`interface *Props` + unions. Seuls les **defaults** diffèrent : ils viennent de `Astro.props` (un
destructuring top-level), pas des paramètres d'une fonction composant.

Requiert l'extra `[astro]` (grammaire astro) ET `[ts]` (grammaire TS pour le frontmatter) ; l'un absent →
détail vide (jamais d'exception). Les NOMS de primitives ne passent pas par ici (filesystem, cf. adaptateur).
"""
from __future__ import annotations

from pathlib import Path

from frontmap import astroparse, tsparse
from frontmap.adapters import tsx_component

_EMPTY: dict = {"props": [], "variants": {}, "defaults": {}, "lead": "", "line": 1}


def _astro_defaults(root_node, data: bytes) -> dict[str, str]:
    """Defaults d'un `const { variant = 'x', … } = Astro.props` (object_pattern du destructuring)."""
    for node in root_node.named_children:
        if node.type not in ("lexical_declaration", "variable_declaration"):
            continue
        for decl in node.named_children:
            if decl.type != "variable_declarator":
                continue
            value = tsparse.field(decl, "value")
            if value is not None and "Astro.props" in tsparse.node_text(data, value):
                pattern = tsparse.field(decl, "name")
                if pattern is not None:
                    return tsx_component.defaults_from_text(tsparse.node_text(data, pattern))
    return {}


def detail(root: Path, astro_rel: str, name: str) -> dict:
    """{props, variants, defaults, lead, line} d'un composant `.astro`. Vide si grammaire astro/TS absente,
    fichier introuvable, ou pas de frontmatter."""
    fpath = Path(root) / astro_rel
    if not astroparse.available() or not fpath.is_file():
        return dict(_EMPTY)
    script = astroparse.frontmatter_script(fpath.read_text(encoding="utf-8"))
    if not script:  # None (pas de frontmatter) ou "" (frontmatter vide)
        return dict(_EMPTY)
    parsed = tsparse.parse(script, "frontmatter.ts")  # le frontmatter Astro est du TS pur (pas de JSX)
    if parsed is None:  # grammaire TS absente
        return dict(_EMPTY)
    root_node, data = parsed
    props, variants = tsx_component.props_and_variants(root_node, data, name)
    return {"props": props, "variants": variants, "defaults": _astro_defaults(root_node, data),
            "lead": "", "line": 1}
