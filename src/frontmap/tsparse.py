"""tsparse — parser TS/TSX partagé (tree-sitter, chargé en LAZY, dégradation GRACIEUSE).

Calqué sur `code-map` (`engines/typescript_ts._parsers`) : tree-sitter est chargé une seule fois et son
absence n'est JAMAIS un point de casse — `available()` renvoie False et les extracteurs qui en dépendent
(primitives, routes) rendent une liste vide. front-map **vendorise le moteur public** `tree-sitter` (même
dép optionnelle que code-map, extra `[ts]`) ; il ne ré-implémente PAS l'extracteur *général* `symindex`.

`Any` (pas `object`) sur les nœuds tree-sitter : la dépendance optionnelle est typée de façon lâche.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_LANG_OF = {".tsx": "tsx", ".ts": "typescript", ".mts": "typescript", ".cts": "typescript"}

# None tant que non initialisé ; {} si tree-sitter indisponible ; sinon lang→Parser.
_PARSERS: dict[str, Any] | None = None


def _parsers() -> dict[str, Any] | None:
    """Map lang→Parser, construite une fois. None si tree-sitter indisponible (best-effort)."""
    global _PARSERS
    if _PARSERS is not None:
        return _PARSERS or None
    try:
        import tree_sitter_typescript as tsts
        from tree_sitter import Language, Parser
    except Exception:  # noqa: BLE001 — lib absente → extraction vide, jamais d'exception remontée
        _PARSERS = {}
        return None
    _PARSERS = {
        "typescript": Parser(Language(tsts.language_typescript())),
        "tsx": Parser(Language(tsts.language_tsx())),
    }
    return _PARSERS


def available() -> bool:
    """True si tree-sitter est installé (l'extraction TSX produira des nœuds)."""
    return _parsers() is not None


def parse(src: str, rel: str) -> tuple[Any, bytes] | None:
    """Parse `src` selon le suffixe de `rel` → (root_node, data_bytes), ou None si tree-sitter absent /
    parse KO. `data_bytes` accompagne le nœud car tree-sitter indexe par offsets d'octets."""
    parsers = _parsers()
    if not parsers:
        return None
    lang = _LANG_OF.get(Path(rel).suffix, "typescript")
    parser = parsers.get(lang) or parsers["typescript"]
    data = src.encode("utf-8", "replace")
    try:
        tree = parser.parse(data)
    except Exception:  # noqa: BLE001
        return None
    return tree.root_node, data


def node_text(data: bytes, node: Any) -> str:
    """Texte source d'un nœud (slice d'octets → str)."""
    return data[node.start_byte:node.end_byte].decode("utf-8", "replace")


def field(node: Any, name: str) -> Any:
    """Enfant nommé `name` d'un nœud, ou None."""
    return node.child_by_field_name(name)


def name_of(data: bytes, node: Any) -> str:
    """Valeur du champ `name` d'un nœud (déclarations), ou chaîne vide."""
    n = node.child_by_field_name("name")
    return node_text(data, n) if n is not None else ""


def lead_comment(data: bytes, node: Any) -> str:
    """1re ligne utile du commentaire JSDoc/`//` précédant une déclaration (best-effort, ≤80c)."""
    prev = node.prev_sibling
    if prev is None or prev.type != "comment":
        return ""
    raw = node_text(data, prev)
    for line in raw.splitlines():
        s = line.strip().lstrip("/").strip().lstrip("*").strip()
        if s.endswith("*/"):
            s = s[:-2].strip()
        if s and not s.startswith("@"):
            return s[:80]
    return ""


def unwrap_export(node: Any) -> Any:
    """Remonte au `export_statement` parent (pour lire le JSDoc posé avant `export`)."""
    p = node.parent
    return p if p is not None and p.type == "export_statement" else node
