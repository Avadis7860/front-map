"""router_react — convention react-router : routes déclarées en JSX `<Route path=… element={<X/>}>`.

Convention du web aggregator (HashRouter). Extrait les `<Route>` **littéraux** (path + composant),
chaîne les parents par imbrication JSX. **Limite assumée, signalée** : la génération DYNAMIQUE de routes
(`{SECTIONS.map(s => <Route …/>)}`, indirection par table) n'est PAS résolue — ce serait de l'analyse de
flot de données spécifique au projet (code-map ne résout pas non plus les imports dynamiques). `signals`
remonte « routes dynamiques non résolues » quand le motif est détecté → jamais de faux-complet. Requiert
tree-sitter ; absent → liste vide (best-effort).
"""
from __future__ import annotations

from pathlib import Path

from frontmap import tsparse
from frontmap.adapters.base import RouteRow
from frontmap.config import Config


def _opening(node):
    """Nœud d'ouverture d'un élément JSX (self-closing = lui-même ; element = son `open_tag`)."""
    if node.type == "jsx_self_closing_element":
        return node
    if node.type == "jsx_element":
        oc = node.child_by_field_name("open_tag")
        if oc is not None:
            return oc
        for c in node.named_children:
            if c.type == "jsx_opening_element":
                return c
    return None


def _elem_name(opening, data: bytes) -> str:
    n = opening.child_by_field_name("name") if opening is not None else None
    return tsparse.node_text(data, n) if n is not None else ""


def _attrs(opening, data: bytes) -> dict:
    """{nom_attribut → nœud_valeur} des `jsx_attribute` d'un élément (valeur None si booléen)."""
    out: dict = {}
    if opening is None:
        return out
    for c in opening.named_children:
        if c.type != "jsx_attribute":
            continue
        kids = c.named_children
        if not kids:
            continue
        name = tsparse.node_text(data, kids[0])
        out[name] = kids[1] if len(kids) > 1 else None
    return out


def _string_val(node, data: bytes) -> str | None:
    if node is not None and node.type == "string":
        return tsparse.node_text(data, node).strip("'\"`")
    return None


def _element_component(node, data: bytes) -> str | None:
    """Nom du composant dans `element={<Comp/>}` (1er élément JSX sous la valeur d'attribut)."""
    if node is None:
        return None

    def find(n):
        if n.type in ("jsx_self_closing_element", "jsx_element"):
            return _elem_name(_opening(n), data) or None
        for c in n.named_children:
            r = find(c)
            if r:
                return r
        return None

    return find(node)


def _contains_call(node) -> bool:
    if node.type == "call_expression":
        return True
    return any(_contains_call(c) for c in node.named_children)


def _full_path(var: str, routes: dict[str, dict], stack: frozenset[str] = frozenset()) -> str:
    if var in stack or var not in routes:
        return ""
    r = routes[var]
    parent, path = r["parent"], r["path"]
    base = _full_path(parent, routes, stack | {var}) if parent in routes else ""
    if path in (None, "", "/"):
        return base or "/"
    if path.startswith("/"):
        return path
    return (base.rstrip("/") + "/" + path) if base else "/" + path


class ReactRouter:
    """Adaptateur router, convention react-router JSX (`RouterAdapter`)."""

    name = "react-router"

    def available(self, root: Path, cfg: Config) -> bool:
        return (Path(root) / cfg.router_file).is_file()

    def referenced_files(self, root: Path, cfg: Config) -> list[str]:
        return [cfg.router_file] if (Path(root) / cfg.router_file).is_file() else []

    def _collect(self, root: Path, cfg: Config) -> tuple[dict[str, dict], bool]:
        """(routes par var, dynamique?) — walk du JSX. `[]`/False si tree-sitter absent ou fichier absent."""
        fpath = Path(root) / cfg.router_file
        if not tsparse.available() or not fpath.is_file():
            return {}, False
        parsed = tsparse.parse(fpath.read_text(encoding="utf-8"), cfg.router_file)
        if parsed is None:
            return {}, False
        root_node, data = parsed
        routes: dict[str, dict] = {}
        state = {"dynamic": False}

        def walk(node, parent_var: str | None) -> None:
            if node.type == "jsx_expression" and _contains_call(node):
                state["dynamic"] = True
            opening = _opening(node)
            name = _elem_name(opening, data) if opening is not None else ""
            child_parent = parent_var
            if name == "Route":
                attrs = _attrs(opening, data)
                path = _string_val(attrs.get("path"), data)
                if "path" in attrs and path is None:
                    # path non littéral (template/expression) → route dynamique, non résolue statiquement.
                    # On la signale sans l'indexer (pas de junk à path=None), et on continue le walk.
                    state["dynamic"] = True
                else:
                    comp = _element_component(attrs.get("element"), data)
                    line = node.start_point[0] + 1
                    var = f"{comp or path or 'route'}@{line}"
                    routes[var] = {"path": path, "component": comp, "parent": parent_var, "line": line}
                    child_parent = var
            elif name == "Routes":
                child_parent = None  # les Route directs sous <Routes> sont au sommet
            for c in node.named_children:
                walk(c, child_parent)

        walk(root_node, None)
        return routes, state["dynamic"]

    def extract_routes(self, root: Path, cfg: Config) -> list[RouteRow]:
        routes, _dyn = self._collect(root, cfg)
        rows: list[RouteRow] = []
        for var, r in routes.items():
            rows.append({"var": var, "path": r["path"], "full_path": _full_path(var, routes),
                         "component": r["component"], "parent": r["parent"], "is_root": False,
                         "file": cfg.router_file, "line": r["line"]})
        rows.sort(key=lambda x: (x["full_path"], x["line"]))
        return rows

    def signals(self, root: Path, cfg: Config) -> list[str]:
        _routes, dynamic = self._collect(root, cfg)
        if dynamic:
            return ["routes react-router générées dynamiquement (`.map`) non résolues — "
                    "seules les routes littérales `<Route>` sont indexées"]
        return []
