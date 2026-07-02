"""tsx_component — détail tree-sitter d'un composant primitive (props/variants/defaults/lead), partagé.

Ce que code-map ne modélise pas (pour lui `Button` est un `kind:function` anonyme) : les **props**
déclarées, les **variantes** (props dont le type est une union de littéraux), les **defaults** (signature
destructurée), le **JSDoc**. Sourcé indifféremment par un barrel (`primitives_barrel`) ou un scan de
dossier (`primitives_dirscan`) — d'où sa vie en module partagé.

Gère plusieurs formes de props : `interface <Name>Props` (convention cockpit) ET `type Props`/`type
<Name>Props = … & { … }` (convention aggregator). Props inline anonymes dans la signature → non modélisées
(best-effort, renvoie vide). Requiert tree-sitter ; absent → détail vide (jamais d'exception).
"""
from __future__ import annotations

import re
from pathlib import Path

from frontmap import tsparse

# `variant?: Variant` (property_signature) → nom, optionnel, type.
_PROP = re.compile(r"(\w+)(\??)\s*:\s*(.+)$", re.S)
# `variant = 'secondary'` (params destructurés) → défauts.
_DEFAULT = re.compile(r"(\w+)\s*=\s*('[^']*'|\"[^\"]*\"|`[^`]*`|[\w.]+)")

_EMPTY: dict = {"props": [], "variants": {}, "defaults": {}, "lead": "", "line": 1}


def _iter_decls(root_node):
    """Déclarations top-level, `export_statement` (y c. `export default`) déballé."""
    for node in root_node.named_children:
        target = node
        if node.type == "export_statement":
            decl = node.child_by_field_name("declaration")
            if decl is None:  # `export default function/const` → pas de champ `declaration`
                for c in node.named_children:
                    if c.type in ("function_declaration", "generator_function_declaration",
                                  "lexical_declaration", "variable_declaration", "class_declaration"):
                        decl = c
                        break
            if decl is not None:
                target = decl
        yield target


def _string_literals(data: bytes, node) -> list[str]:
    out: list[str] = []

    def walk(n) -> None:
        if n.type == "string":
            out.append(tsparse.node_text(data, n).strip("'\"`"))
        for c in n.named_children:
            walk(c)

    if node is not None:
        walk(node)
    return out


def _union_types(root_node, data: bytes) -> dict[str, list[str]]:
    """`type X = 'a' | 'b'` → {X: [a, b]} (unions de littéraux string)."""
    unions: dict[str, list[str]] = {}
    for node in _iter_decls(root_node):
        if node.type == "type_alias_declaration":
            vals = _string_literals(data, tsparse.field(node, "value"))
            if vals:
                unions[tsparse.name_of(data, node)] = vals
    return unions


def _object_props(body, data: bytes) -> list[dict]:
    """Props (property_signature) d'un nœud `object_type`/`interface_body`."""
    props: list[dict] = []
    if body is None:
        return props
    for m in body.named_children:
        if m.type != "property_signature":
            continue
        raw = tsparse.node_text(data, m).strip().rstrip(";").strip()
        pm = _PROP.match(raw)
        if pm:
            props.append({"name": pm.group(1), "type": pm.group(3).strip(),
                          "optional": bool(pm.group(2))})
    return props


def _find_object_type(node):
    """1er `object_type` sous `node` (pour `type Props = X & { … }`)."""
    if node is None:
        return None
    if node.type == "object_type":
        return node
    for c in node.named_children:
        found = _find_object_type(c)
        if found is not None:
            return found
    return None


def _props(root_node, data: bytes, primitive: str) -> list[dict]:
    """Props de `interface <Name>Props` (sinon 1re interface `*Props`, sinon `type (<Name>)Props = …`)."""
    interfaces: list = []
    type_aliases: list = []
    for node in _iter_decls(root_node):
        iname = tsparse.name_of(data, node)
        if node.type == "interface_declaration" and iname.endswith("Props"):
            interfaces.append((iname, node))
        elif node.type == "type_alias_declaration" and iname.endswith("Props"):
            type_aliases.append((iname, node))
    for iname, node in interfaces:
        if iname == f"{primitive}Props":
            return _object_props(tsparse.field(node, "body"), data)
    if interfaces:
        return _object_props(tsparse.field(interfaces[0][1], "body"), data)
    for iname, node in type_aliases:
        if iname in (f"{primitive}Props", "Props"):
            return _object_props(_find_object_type(tsparse.field(node, "value")), data)
    if type_aliases:
        return _object_props(_find_object_type(tsparse.field(type_aliases[0][1], "value")), data)
    return []


def _component(root_node, data: bytes, name: str):
    """Nœud fonction/const du composant `name`, ou le `export default function` (nommé ou anonyme)."""
    default_fn = None
    for node in _iter_decls(root_node):
        if (node.type in ("function_declaration", "generator_function_declaration")):
            if tsparse.name_of(data, node) == name:
                return node
            if default_fn is None:
                default_fn = node
        if node.type in ("lexical_declaration", "variable_declaration"):
            for d in node.named_children:
                if d.type == "variable_declarator" and tsparse.name_of(data, d) == name:
                    val = tsparse.field(d, "value")
                    if val is not None and val.type in ("arrow_function", "function_expression"):
                        return val
    return default_fn


def _defaults(comp_node, data: bytes) -> dict[str, str]:
    if comp_node is None:
        return {}
    params = tsparse.field(comp_node, "parameters")
    if params is None:
        return {}
    text = tsparse.node_text(data, params)
    return {k: v.strip("'\"`") for k, v in _DEFAULT.findall(text)}


def detail(root: Path, tsx_rel: str, name: str) -> dict:
    """{props, variants, defaults, lead, line} d'un composant. Vide si TS absent/fichier introuvable."""
    fpath = Path(root) / tsx_rel
    if not tsparse.available() or not fpath.is_file():
        return dict(_EMPTY)
    parsed = tsparse.parse(fpath.read_text(encoding="utf-8"), tsx_rel)
    if parsed is None:
        return dict(_EMPTY)
    root_node, data = parsed
    props = _props(root_node, data, name)
    comp = _component(root_node, data, name)
    unions = _union_types(root_node, data)
    variants = {p["name"]: unions[p["type"]] for p in props if p["type"] in unions}
    line = (comp.start_point[0] + 1) if comp is not None else 1
    lead = tsparse.lead_comment(data, tsparse.unwrap_export(comp)) if comp is not None else ""
    return {"props": props, "variants": variants, "defaults": _defaults(comp, data),
            "lead": lead, "line": line}
