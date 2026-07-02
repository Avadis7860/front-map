"""adapters — genericité multi-convention : auto-détection + 2e convention (react-router + dir-scan).

Prouve que front-map indexe un projet à convention DIFFÉRENTE du cockpit (react-router JSX + primitives en
`export default` sans barrel), et que la détection route bien vers le bon adaptateur. Le cœur (détection,
noms de primitives, usage) est pur-Python → testé sans skipif ; l'extraction TSX riche est gardée.
"""
from __future__ import annotations

import pytest

from conftest import FIXTURES, RR
from frontmap import adapters, query, tsparse
from frontmap.adapters.primitives_dirscan import DirScanPrimitives
from frontmap.adapters.router_react import ReactRouter
from frontmap.build import build
from frontmap.config import Config

_TS = tsparse.available()


def test_autodetect_conventions_per_project(cfg, cfg_rr):
    # projet 1 (cockpit) : TanStack + barrel
    d1 = adapters.detect(FIXTURES, cfg)
    assert d1["router"] == "tanstack"
    assert d1["primitives"] == "barrel"
    # projet 2 (rr-app) : react-router + dir-scan
    d2 = adapters.detect(RR, cfg_rr)
    assert d2["router"] == "react-router"
    assert d2["primitives"] == "dir-scan"
    assert d2["primitives_available"] is True


def test_config_override_forces_convention():
    forced = Config(router_flavor="react-router", primitives_source="dir-scan")
    assert adapters.resolve_router(FIXTURES, forced).name == "react-router"
    assert adapters.resolve_primitives(FIXTURES, forced).name == "dir-scan"


def test_dirscan_primitive_names_without_treesitter(cfg_rr, monkeypatch):
    # noms via filesystem (stem de fichier) → aucun tree-sitter requis (contrat pivot pour `usage`)
    monkeypatch.setattr(tsparse, "_PARSERS", {})
    names = DirScanPrimitives().primitive_names(RR, cfg_rr)
    assert names == {"Button", "Badge"}


def test_react_router_static_routes_and_dynamic_signal(cfg_rr):
    if not _TS:
        pytest.skip("tree-sitter absent (extra [ts])")
    rr = ReactRouter()
    paths = {r["full_path"] for r in rr.extract_routes(RR, cfg_rr)}
    assert "/" in paths and "/settings" in paths
    # la route générée par `.map` (path template) n'est PAS indexée…
    assert not any(p.startswith("/dyn/") for p in paths)
    # …mais elle est SIGNALÉE (honnête, pas faux-complet)
    assert any("dynamiquement" in s for s in rr.signals(RR, cfg_rr))


def test_genericity_usage_on_rr_app(tmp_path, cfg_rr):
    """Le critère binaire : `consumers` sort des primitives sur un projet react-router + dir-scan."""
    build(RR, tmp_path, cfg_rr)
    home = query.consumers(tmp_path, "Home.tsx")["consumer"]
    assert home["primitives"] == ["Button"]                 # import par défaut détecté (dir-scan)
    assert home["tokens"] == ["--color-accent-500"]
    settings = query.consumers(tmp_path, "Settings.tsx")["consumer"]
    assert settings["primitives"] == ["Badge"]
    # index inversé cohérent
    assert any(c["consumer"].endswith("Home.tsx") for c in query.usage(tmp_path, "Button")["as_primitive"])


def test_build_traces_convention_in_manifest(tmp_path, cfg_rr):
    res = build(RR, tmp_path, cfg_rr)
    assert res["conventions"] == {"router": "react-router", "primitives": "dir-scan"}
    chk = query.check(tmp_path, RR, cfg_rr)
    assert chk["conventions"]["primitives"] == "dir-scan"
    assert chk["fresh"] is True
