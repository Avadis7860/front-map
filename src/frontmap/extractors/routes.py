"""routes — extracteur de l'**arbre des routes** (TanStack Router code-based, TSX via tree-sitter).

Parse les appels `createRoute({ path, component, getParentRoute })` (+ `createRootRoute`) du fichier de
routage (défaut `web/src/router.tsx`), puis reconstruit le `full_path` de chaque route en chaînant ses
parents (`/$project` + `gate` → `/$project/gate`). Répond « quelle route rend telle vue ? » — une
sémantique que code-map (qui ne voit que des `const` et des appels) ne modélise pas.

Requiert tree-sitter (extra `[ts]`). Absent → dégradation gracieuse (liste vide).
"""
from __future__ import annotations

from pathlib import Path

from frontmap import tsparse

ENGINE = "tree-sitter-routes-v1"
_ROUTE_FACTORIES = ("createRoute", "createRootRoute")


def _iter_decls(root_node):
    for node in root_node.named_children:
        target = node
        if node.type == "export_statement":
            decl = node.child_by_field_name("declaration")
            if decl is not None:
                target = decl
        yield target


def _first_object(node):
    """1er nœud `object` sous `node` (l'argument objet d'un `createRoute({…})`)."""
    if node is None:
        return None
    for c in node.named_children:
        if c.type == "object":
            return c
    return None


def _arrow_return_ident(data: bytes, val) -> str | None:
    """`() => rootRoute` → `rootRoute` (identifiant retourné par la flèche `getParentRoute`)."""
    if val is None or val.type not in ("arrow_function", "function_expression"):
        return None
    body = tsparse.field(val, "body")
    if body is None:
        return None
    return tsparse.node_text(data, body).strip().strip("()").strip() or None


def _parse_route_object(obj, data: bytes) -> dict:
    res: dict = {"path": None, "component": None, "parent": None}
    if obj is None:
        return res
    for pair in obj.named_children:
        if pair.type != "pair":
            continue
        key = tsparse.field(pair, "key")
        val = tsparse.field(pair, "value")
        if key is None or val is None:
            continue
        kname = tsparse.node_text(data, key).strip("'\"")
        if kname == "path":
            res["path"] = tsparse.node_text(data, val).strip("'\"`")
        elif kname == "component":
            res["component"] = tsparse.node_text(data, val)
        elif kname == "getParentRoute":
            res["parent"] = _arrow_return_ident(data, val)
    return res


def _route_calls(root_node, data: bytes) -> dict[str, dict]:
    """Map `varname → {path, component, parent, is_root, line}` pour chaque route déclarée."""
    routes: dict[str, dict] = {}
    for node in _iter_decls(root_node):
        if node.type not in ("lexical_declaration", "variable_declaration"):
            continue
        for d in node.named_children:
            if d.type != "variable_declarator":
                continue
            val = tsparse.field(d, "value")
            if val is None or val.type != "call_expression":
                continue
            callee = tsparse.field(val, "function")
            cname = tsparse.node_text(data, callee) if callee is not None else ""
            if cname not in _ROUTE_FACTORIES:
                continue
            info = _parse_route_object(_first_object(tsparse.field(val, "arguments")), data)
            info["is_root"] = cname == "createRootRoute"
            info["line"] = d.start_point[0] + 1
            routes[tsparse.name_of(data, d)] = info
    return routes


def _full_path(var: str, routes: dict[str, dict], stack: frozenset[str] = frozenset()) -> str:
    """`full_path` d'une route, chaîné via ses parents. `stack` coupe un éventuel cycle."""
    if var in stack or var not in routes:
        return ""
    r = routes[var]
    parent, path = r["parent"], r["path"]
    if parent is None or parent not in routes:
        return path or ""
    base = _full_path(parent, routes, stack | {var})
    if path in (None, "", "/"):
        return base or "/"
    if path.startswith("/"):
        return path if base in ("", "/") else base.rstrip("/") + path
    return base.rstrip("/") + "/" + path


def extract_routes(root: Path, router_file: str) -> list[dict]:
    """Routes déclarées dans `router_file`. `[]` si tree-sitter absent ou fichier introuvable."""
    root = Path(root)
    fpath = root / router_file
    if not tsparse.available() or not fpath.is_file():
        return []
    parsed = tsparse.parse(fpath.read_text(encoding="utf-8"), router_file)
    if parsed is None:
        return []
    root_node, data = parsed
    routes = _route_calls(root_node, data)
    rows: list[dict] = []
    for var, r in routes.items():
        rows.append({
            "var": var, "path": r["path"], "full_path": _full_path(var, routes),
            "component": r["component"], "parent": r["parent"],
            "is_root": r["is_root"], "file": router_file, "line": r["line"],
        })
    rows.sort(key=lambda x: (x["full_path"], x["line"]))
    return rows
