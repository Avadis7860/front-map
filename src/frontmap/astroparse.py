"""astroparse — parseur Astro (tree-sitter via `tree-sitter-language-pack`, LAZY, dégradation GRACIEUSE).

Rôle UNIQUE : délimiter le `frontmatter_js_block` d'un fichier `.astro` — le TS entre les `---`. La grammaire
astro laisse ce bloc **opaque** (elle ne parse pas le TS qu'il contient) ; on renvoie donc son **texte**, que
l'appelant re-parse avec la grammaire TS déjà présente (`tsparse`) pour en tirer props/variants/defaults.
C'est l'« injection de langage » faite à la main : astro pour la structure, TS pour le frontmatter.

Calqué sur `tsparse` : la lib est chargée une seule fois et son absence n'est JAMAIS un point de casse —
`available()` renvoie False et l'extraction du détail dégrade à vide (les NOMS de primitives, eux, restent
connus car ils viennent du filesystem). Il n'existe pas de wheel `tree-sitter-astro` autonome sur PyPI : la
grammaire est fournie, pré-compilée, par `tree-sitter-language-pack` (extra optionnel `[astro]`).

`Any` (pas `object`) sur le parser tree-sitter : la dépendance optionnelle est typée de façon lâche.
"""
from __future__ import annotations

from typing import Any

# None tant que non tenté ; sinon Parser astro ou None si la lib est absente.
_PARSER: Any | None = None
_TRIED = False


def _parser() -> Any | None:
    """Parser astro, construit une fois. None si `tree-sitter-language-pack` indisponible (best-effort)."""
    global _PARSER, _TRIED
    if _TRIED:
        return _PARSER
    _TRIED = True
    try:
        from tree_sitter_language_pack import get_parser
        _PARSER = get_parser("astro")
    except Exception:  # noqa: BLE001 — lib absente / grammaire manquante → détail vide, jamais d'exception
        _PARSER = None
    return _PARSER


def available() -> bool:
    """True si la grammaire astro est chargeable (l'extraction du frontmatter produira des nœuds)."""
    return _parser() is not None


def frontmatter_script(src: str) -> str | None:
    """Texte du `frontmatter_js_block` d'un `.astro` (le TS entre les `---`, fences EXCLUES).

    None si la grammaire astro est absente, si le parse échoue, ou si le fichier n'a pas de frontmatter.
    Chaîne vide si le frontmatter existe mais est vide."""
    parser = _parser()
    if parser is None:
        return None
    data = src.encode("utf-8", "replace")
    try:
        tree = parser.parse(data)
    except Exception:  # noqa: BLE001
        return None
    for node in tree.root_node.named_children:
        if node.type == "frontmatter":
            for child in node.named_children:
                if child.type == "frontmatter_js_block":
                    return data[child.start_byte:child.end_byte].decode("utf-8", "replace")
            return ""  # frontmatter présent mais vide (`---\n---`)
    return None  # aucun frontmatter
