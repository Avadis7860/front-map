"""dégradation gracieuse — tree-sitter absent : primitives/routes vides, tokens OK, jamais d'exception."""
from __future__ import annotations

from conftest import BARREL, FIXTURES, ROUTER
from frontmap import query, tsparse
from frontmap.build import build
from frontmap.extractors import primitives, routes


def _force_no_treesitter(monkeypatch):
    # `_parsers()` renvoie `_PARSERS or None` → un dict vide simule tree-sitter indisponible.
    monkeypatch.setattr(tsparse, "_PARSERS", {})
    assert tsparse.available() is False


def test_primitives_and_routes_empty_without_treesitter(monkeypatch):
    _force_no_treesitter(monkeypatch)
    assert primitives.extract_primitives(FIXTURES, BARREL) == []
    assert routes.extract_routes(FIXTURES, ROUTER) == []


def test_build_still_produces_tokens_and_check_flags_absence(tmp_path, cfg, monkeypatch):
    _force_no_treesitter(monkeypatch)
    res = build(FIXTURES, tmp_path, cfg)
    assert res["skipped"] is False
    assert res["counts"]["tokens"] > 0        # tokens (CSS pur) toujours produits
    assert res["counts"]["primitives"] == 0
    assert res["counts"]["routes"] == 0

    chk = query.check(tmp_path, FIXTURES, cfg)
    assert chk["ts_available"] is False
    assert any("tree-sitter" in f for f in chk["findings"])


def test_usage_still_works_without_treesitter(tmp_path, cfg, monkeypatch):
    # usage est PUR-Python (barrel + imports en regex) → produit même sans tree-sitter ; seul le lien
    # route se dégrade à None (routes vide).
    _force_no_treesitter(monkeypatch)
    res = build(FIXTURES, tmp_path, cfg)
    assert res["counts"]["usage"] > 0
    assert query.usage(tmp_path, "Button")["count"] >= 2   # Home + Workspace

    home = query.consumers(tmp_path, "Home.tsx")["consumer"]
    assert "Button" in home["primitives"]
    assert home["route"] is None                            # non résolu sans tree-sitter
