"""tokens — extracteur des **design tokens** depuis le CSS (véhicule UNIQUE du design-system).

CSS pur, **zéro tree-sitter** : parse les custom properties (`--x: v;`) des blocs `@theme { … }` et
`:root { … }` d'un fichier de tokens (défaut `web/src/index.css`). Toujours disponible (socle stdlib).

`group` dérivé du préfixe du nom — donne la sémantique que code-map ne modélise pas (pour lui un token
n'est qu'un `const`) : `--color-accent-*`→`accent` · `--color-{ok,warn,danger,info,purple}-*`→`status` ·
autres `--color-*`→`surface` · `--radius-*`→`radius` · `--shadow-*`→`shadow` · `--animate-*`→`motion` ·
`--font-*`→`typography` · `--z-*`→`z`. `lead` = titre de la section (dernier commentaire de bloc).
"""
from __future__ import annotations

import re

ENGINE = "css-tokens-v1"

_STATUS_ROLES = frozenset({"ok", "warn", "danger", "info", "purple"})
_DECL = re.compile(r"\s*(--[\w-]+)\s*:\s*(.+?)\s*;")


def group_of(name: str) -> str:
    """Groupe sémantique d'un token, dérivé du préfixe de son nom."""
    if name.startswith("--color-"):
        base = name[len("--color-"):].split("-", 1)[0]
        if base == "accent":
            return "accent"
        if base in _STATUS_ROLES:
            return "status"
        return "surface"
    for prefix, grp in (("--radius-", "radius"), ("--shadow-", "shadow"), ("--animate-", "motion"),
                        ("--font-", "typography"), ("--z-", "z")):
        if name.startswith(prefix):
            return grp
    return "other"


def _section_title(comment_text: str) -> str:
    """1re ligne porteuse de lettres d'un commentaire de bloc, décoration retirée (≤80c)."""
    for line in comment_text.splitlines():
        s = line.strip().strip("*").strip("─-").strip()
        if any(c.isalpha() for c in s):
            return s[:80]
    return ""


def _iter_code_lines(css: str):
    """Yield `(lineno, code_sans_commentaire, section)` — commentaires `/* */` retirés (multi-lignes
    gérées), `section` = titre du dernier commentaire de bloc fermé (contexte des tokens qui suivent)."""
    in_comment = False
    buf: list[str] = []
    section = ""
    for lineno, raw in enumerate(css.split("\n"), 1):
        code: list[str] = []
        j, s = 0, raw
        while j < len(s):
            if in_comment:
                end = s.find("*/", j)
                if end == -1:
                    buf.append(s[j:])
                    break
                buf.append(s[j:end])
                section = _section_title("".join(buf))
                buf = []
                in_comment = False
                j = end + 2
            else:
                start = s.find("/*", j)
                if start == -1:
                    code.append(s[j:])
                    break
                code.append(s[j:start])
                in_comment = True
                j = start + 2
        yield lineno, "".join(code), section


def extract_tokens(css_text: str, source_file: str) -> list[dict]:
    """Tokens d'un fichier CSS. `source_file` = chemin POSIX relatif (pour l'ancrage). Déterministe."""
    rows: list[dict] = []
    for lineno, code, section in _iter_code_lines(css_text):
        m = _DECL.match(code)
        if not m:
            continue
        name, value = m.group(1), m.group(2).strip()
        rows.append({
            "name": name, "value": value, "group": group_of(name),
            "source_file": source_file, "line": lineno, "lead": section,
        })
    return rows
