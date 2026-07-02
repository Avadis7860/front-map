"""tokens — extraction CSP pure (aucun tree-sitter requis)."""
from __future__ import annotations

from collections import defaultdict

from conftest import FIXTURES, TOKENS
from frontmap.extractors import tokens


def _rows():
    css = (FIXTURES / TOKENS).read_text(encoding="utf-8")
    return tokens.extract_tokens(css, TOKENS)


def test_group_derivation_by_prefix():
    assert tokens.group_of("--color-accent-500") == "accent"
    assert tokens.group_of("--color-danger-500") == "status"
    assert tokens.group_of("--color-ok-500") == "status"
    assert tokens.group_of("--color-surface") == "surface"
    assert tokens.group_of("--color-bg") == "surface"
    assert tokens.group_of("--radius-card") == "radius"
    assert tokens.group_of("--shadow-raised") == "shadow"
    assert tokens.group_of("--animate-enter") == "motion"
    assert tokens.group_of("--font-sans") == "typography"
    assert tokens.group_of("--z-header") == "z"


def test_extracts_theme_and_root_blocks():
    rows = _rows()
    by_group: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r["name"])
    assert set(by_group["accent"]) == {"--color-accent-400", "--color-accent-500"}
    assert set(by_group["status"]) == {"--color-ok-500", "--color-danger-500"}
    assert set(by_group["surface"]) == {"--color-bg", "--color-surface", "--color-fg"}
    # :root (hors @theme) est bien capturé
    assert set(by_group["z"]) == {"--z-header", "--z-overlay"}


def test_value_line_and_comment_stripped():
    row = next(r for r in _rows() if r["name"] == "--radius-card")
    assert row["value"] == "0.625rem"          # commentaire inline retiré
    assert row["line"] > 0
    assert row["source_file"] == TOKENS
