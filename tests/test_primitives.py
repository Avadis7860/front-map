"""primitives — extraction TSX (props, variantes, defaults). Requiert tree-sitter."""
from __future__ import annotations

import pytest

from conftest import BARREL, FIXTURES
from frontmap import tsparse
from frontmap.extractors import primitives

pytestmark = pytest.mark.skipif(not tsparse.available(), reason="tree-sitter absent (extra [ts])")


def _by_name():
    return {p["name"]: p for p in primitives.extract_primitives(FIXTURES, BARREL)}


def test_barrel_is_authority_for_primitive_list():
    assert set(_by_name()) == {"Button", "Badge"}


def test_button_variants_props_defaults_lead():
    b = _by_name()["Button"]
    assert b["variants"]["variant"] == ["primary", "secondary", "ghost", "danger"]
    assert b["variants"]["size"] == ["sm", "md"]
    assert b["defaults"] == {"variant": "secondary", "size": "md", "busy": "false"}
    assert {p["name"] for p in b["props"]} == {"variant", "size", "busy"}
    assert b["file"] == "web/src/components/ui/Button.tsx"
    assert "action primaire" in b["lead"]


def test_badge_single_variant_axis():
    badge = _by_name()["Badge"]
    assert badge["variants"] == {"tone": ["ok", "warn", "danger"]}
    # `label` (type string, non-union) n'est PAS une variante
    assert "label" not in badge["variants"]
    assert any(p["name"] == "label" and not p["optional"] for p in badge["props"])
