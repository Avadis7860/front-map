"""imports — parsing LÉGER des imports ES (regex, pur-Python), partagé par usage + adaptateurs primitives.

Front-map ne modélise PAS le graphe d'imports général (ça, c'est code-map). On ne lit QUE ce qu'il faut
pour relier un écran au vocabulaire connu : imports **nommés** (`import { Button } from '…'`, convention
barrel) et imports **par défaut** (`import Button from '…/Button'`, convention dir-scan). Regex = pas de
tree-sitter → l'index inverse reste exploitable sans l'extra `[ts]`.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# `import { A, B as C } from '…'` (multiligne via re.S) — (type-only?, spécificateurs, source).
_NAMED = re.compile(r"import\s+(type\s+)?\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]", re.S)
# `import Button from '…'` — un identifiant par défaut (pas de `{`), source. Exclut `import type X`.
_DEFAULT = re.compile(r"import\s+(?!type\s)([A-Za-z_$][\w$]*)\s*(?:,\s*\{[^}]*\})?"
                      r"\s*from\s*['\"]([^'\"]+)['\"]")


def resolve_module(source: str, importer_rel: str, web_root: str, alias: str = "@/") -> str | None:
    """Chemin rel (sans extension) d'un import LOCAL. `<alias>x`→`<web_root>/x` ; `./x`/`../x` relatif au
    fichier importateur. None pour un import de package nu (`react`, `@tanstack/…`) — non local."""
    s = source.strip("'\"`")
    if alias and s.startswith(alias):
        rel = f"{web_root}/{s[len(alias):]}"
    elif s.startswith(("./", "../")):
        rel = os.path.normpath(str(Path(importer_rel).parent / s)).replace(os.sep, "/")
    else:
        return None
    return rel.rstrip("/")


def named_imports(text: str) -> list[tuple[str, list[str]]]:
    """(source, [noms de VALEUR importés]) pour chaque `import { … } from '…'` (type-only ignoré)."""
    out: list[tuple[str, list[str]]] = []
    for m in _NAMED.finditer(text):
        if m.group(1):  # `import type { … }` → tout l'import est type-only
            continue
        names: list[str] = []
        for spec in m.group(2).split(","):
            spec = spec.strip()
            if not spec or spec.startswith("type "):  # `{ type X, Button }` → spécificateur type inline
                continue
            names.append(spec.split(" as ")[0].strip())
        out.append((m.group(3), names))
    return out


def default_imports(text: str) -> list[tuple[str, str]]:
    """(source, nom_local) pour chaque `import X from '…'` (import par défaut). `X` est l'alias local."""
    return [(m.group(2), m.group(1)) for m in _DEFAULT.finditer(text)]
