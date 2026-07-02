"""routes — adaptateur TanStack (full_path chaîné). Requiert tree-sitter."""
from __future__ import annotations

import pytest

from conftest import FIXTURES
from frontmap import tsparse
from frontmap.adapters.router_tanstack import TanstackRouter
from frontmap.config import Config

pytestmark = pytest.mark.skipif(not tsparse.available(), reason="tree-sitter absent (extra [ts])")


def _by_var():
    return {r["var"]: r for r in TanstackRouter().extract_routes(FIXTURES, Config())}


def test_full_path_chained_via_parents():
    by = _by_var()
    assert by["indexRoute"]["full_path"] == "/"
    assert by["wsRoute"]["full_path"] == "/$project"
    assert by["gateRoute"]["full_path"] == "/$project/gate"


def test_component_and_root_flag():
    by = _by_var()
    assert by["gateRoute"]["component"] == "GatePanel"
    assert by["rootRoute"]["is_root"] is True
    assert by["gateRoute"]["parent"] == "wsRoute"
    # createRouter(...) n'est pas une route
    assert "router" not in by
