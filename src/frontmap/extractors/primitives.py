"""primitives — extracteur du **catalogue de primitives** du design-system (TSX via tree-sitter).

Autorité = le **barrel** `components/ui/index.ts` (ses exports de valeur = la liste canonique des
primitives — doctrine « plus aucun écran sans passer par ici »). Pour chaque primitive, on ouvre le `.tsx`
frère et on extrait ce que code-map **ne modélise pas** (pour lui `Button` n'est qu'un `kind:function`) :
- les **props** déclarées (interface `<Name>Props`) : nom, type, optionnel ;
- les **variantes** : props dont le type est une union de littéraux (`type Variant = 'a'|'b'`) → valeurs ;
- les **defaults** : valeurs par défaut lues dans la signature destructurée (`variant = 'secondary'`).

Requiert tree-sitter (extra `[ts]`). Absent → **dégradation gracieuse** : liste vide (jamais d'exception ;
`build`/`check` le signalent). CSS des tokens reste, lui, toujours disponible.
"""
from __future__ import annotations

import re
from pathlib import Path

from frontmap import tsparse

ENGINE = "tree-sitter-primitives-v1"

# `export { Button, type ButtonProps } from './Button'` — capture specifiers + module.
_BARREL = re.compile(r"export\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]")
# `variant?: Variant` (dans un property_signature) → nom, optionnel, type.
_PROP = re.compile(r"(\w+)(\??)\s*:\s*(.+)$", re.S)
# `variant = 'secondary'` (dans les params destructurés) → défauts.
_DEFAULT = re.compile(r"(\w+)\s*=\s*('[^']*'|\"[^\"]*\"|`[^`]*`|[\w.]+)")


def parse_barrel(barrel_text: str) -> list[dict]:
    """Primitives déclarées par le barrel : `{name, module}` (exports de VALEUR seuls ; `type X` ignorés)."""
    out: list[dict] = []
    for m in _BARREL.finditer(barrel_text):
        names = []
        for spec in m.group(1).split(","):
            spec = spec.strip()
            if not spec or spec.startswith("type "):
                continue
            names.append(spec.split(" as ")[0].strip())
        if names:
            out.append({"name": names[0], "module": m.group(2)})
    return out


def resolve_tsx(barrel_file: str, module: str) -> str:
    """Chemin POSIX relatif du `.tsx` d'une primitive, résolu depuis le dossier du barrel."""
    base = Path(barrel_file).parent
    return (base / (module.lstrip("./") + ".tsx")).as_posix()


def referenced_files(root: Path, barrel_file: str) -> list[str]:
    """Fichiers sources consommés (barrel + chaque `.tsx` existant) — pour le hash de fraîcheur."""
    root = Path(root)
    bpath = root / barrel_file
    if not bpath.is_file():
        return []
    files = [barrel_file]
    for entry in parse_barrel(bpath.read_text(encoding="utf-8")):
        tsx = resolve_tsx(barrel_file, entry["module"])
        if (root / tsx).is_file():
            files.append(tsx)
    return files


def _iter_decls(root_node):
    """Déclarations top-level, `export_statement` déballé (comme `typescript_ts`)."""
    for node in root_node.named_children:
        target = node
        if node.type == "export_statement":
            decl = node.child_by_field_name("declaration")
            if decl is not None:
                target = decl
        yield target


def _string_literals(data: bytes, node) -> list[str]:
    """Toutes les chaînes littérales sous `node` (pour les unions `'a' | 'b'`)."""
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
    """`type X = 'a' | 'b'` → {X: [a, b]} (unions de littéraux string uniquement)."""
    unions: dict[str, list[str]] = {}
    for node in _iter_decls(root_node):
        if node.type == "type_alias_declaration":
            val = tsparse.field(node, "value")
            vals = _string_literals(data, val)
            if vals:
                unions[tsparse.name_of(data, node)] = vals
    return unions


def _props(root_node, data: bytes, primitive: str) -> tuple[str, list[dict]]:
    """Props de l'interface `<Name>Props` (sinon 1re interface `*Props`) : nom, type, optionnel."""
    chosen = None
    for node in _iter_decls(root_node):
        if node.type == "interface_declaration":
            iname = tsparse.name_of(data, node)
            if iname == f"{primitive}Props":
                chosen = node
                break
            if iname.endswith("Props") and chosen is None:
                chosen = node
    if chosen is None:
        return "", []
    body = tsparse.field(chosen, "body")
    props: list[dict] = []
    if body is not None:
        for m in body.named_children:
            if m.type != "property_signature":
                continue
            raw = tsparse.node_text(data, m).strip().rstrip(";").strip()
            pm = _PROP.match(raw)
            if pm:
                props.append({"name": pm.group(1), "type": pm.group(3).strip(),
                              "optional": bool(pm.group(2))})
    return tsparse.name_of(data, chosen), props


def _component(root_node, data: bytes, name: str):
    """Nœud de la fonction composant (déclaration ou const fléchée) portant `name`, ou None."""
    for node in _iter_decls(root_node):
        if (node.type in ("function_declaration", "generator_function_declaration")
                and tsparse.name_of(data, node) == name):
            return node
        if node.type in ("lexical_declaration", "variable_declaration"):
            for d in node.named_children:
                if d.type == "variable_declarator" and tsparse.name_of(data, d) == name:
                    val = tsparse.field(d, "value")
                    if val is not None and val.type in ("arrow_function", "function_expression"):
                        return val
    return None


def _defaults(comp_node, data: bytes) -> dict[str, str]:
    """Defaults lus dans les params destructurés (`{ variant = 'secondary', … }`)."""
    if comp_node is None:
        return {}
    params = tsparse.field(comp_node, "parameters")
    if params is None:
        return {}
    text = tsparse.node_text(data, params)
    return {k: v.strip("'\"`") for k, v in _DEFAULT.findall(text)}


def extract_primitives(root: Path, barrel_file: str) -> list[dict]:
    """Primitives du design-system. `[]` si tree-sitter absent ou barrel introuvable (best-effort)."""
    root = Path(root)
    bpath = root / barrel_file
    if not tsparse.available() or not bpath.is_file():
        return []
    rows: list[dict] = []
    for entry in parse_barrel(bpath.read_text(encoding="utf-8")):
        name = entry["name"]
        tsx = resolve_tsx(barrel_file, entry["module"])
        fpath = root / tsx
        if not fpath.is_file():
            continue
        parsed = tsparse.parse(fpath.read_text(encoding="utf-8"), tsx)
        if parsed is None:
            continue
        root_node, data = parsed
        _, props = _props(root_node, data, name)
        comp = _component(root_node, data, name)
        unions = _union_types(root_node, data)
        variants = {p["name"]: unions[p["type"]] for p in props if p["type"] in unions}
        line = (comp.start_point[0] + 1) if comp is not None else 1
        lead = tsparse.lead_comment(data, tsparse.unwrap_export(comp)) if comp is not None else ""
        rows.append({
            "name": name, "file": tsx, "line": line, "props": props,
            "variants": variants, "defaults": _defaults(comp, data), "lead": lead,
        })
    return rows
