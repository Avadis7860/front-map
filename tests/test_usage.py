"""usage — index inverse : primitives importées du barrel + tokens littéraux + lien route.

Le cœur (primitives + tokens) est PUR-Python (regex) → testé sans skipif. Seul le lien route dépend de
`routes` (tree-sitter) → son test est gardé.
"""
from __future__ import annotations

import pytest

from conftest import FIXTURES
from frontmap import tsparse
from frontmap.extractors import primitives, routes, tokens, usage


def _rows(cfg):
    prim_names = primitives.primitive_names(FIXTURES, cfg.primitives_barrel)
    tok_names = {t["name"] for t in tokens.extract_tokens(
        (FIXTURES / cfg.tokens_file).read_text(encoding="utf-8"), cfg.tokens_file)}
    rts = routes.extract_routes(FIXTURES, cfg.router_file)
    return {r["consumer"]: r for r in usage.extract_usage(FIXTURES, cfg, prim_names, tok_names, rts)}


def test_primitive_usage_from_barrel_imports(cfg):
    by = _rows(cfg)
    home = by["web/src/pages/Home.tsx"]
    assert home["primitives"] == ["Badge", "Button"]   # `import { Badge, Button } from '@/components/ui'`
    assert home["kind"] == "page"
    assert by["web/src/pages/Workspace.tsx"]["primitives"] == ["Button"]


def test_token_usage_literal(cfg):
    by = _rows(cfg)
    assert by["web/src/pages/Home.tsx"]["tokens"] == ["--color-accent-500"]
    assert by["web/src/pages/GatePanel.tsx"]["tokens"] == ["--color-danger-500"]


def test_non_consumers_omitted(cfg):
    by = _rows(cfg)
    # AppShell (aucune primitive/token) et lib/util.ts (pur) ne sont PAS des consommateurs du DS
    assert "web/src/App.tsx" not in by
    assert "web/src/lib/util.ts" not in by


@pytest.mark.skipif(not tsparse.available(), reason="tree-sitter absent (extra [ts])")
def test_route_linkage_when_component_of_a_route(cfg):
    by = _rows(cfg)
    assert by["web/src/pages/Home.tsx"]["route"] == "/"
    assert by["web/src/pages/Workspace.tsx"]["route"] == "/$project"
    assert by["web/src/pages/GatePanel.tsx"]["route"] == "/$project/gate"
