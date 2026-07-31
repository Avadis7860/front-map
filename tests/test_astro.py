"""astro — 3e convention primitives : détection filesystem + détail par injection astro→TS + `check` honnête.

Le cœur (détection, noms de primitives, résolution d'import) est pur-Python → testé sans skipif ; l'extraction
riche (props/variants/defaults) exige la grammaire astro (`tree-sitter-language-pack`, extra `[astro]`) ET TS
(`[ts]`) → gardée. Le critère central du backlog : `frontmap check` ne se lit JAMAIS faux-vert sur une source
`.astro` qu'il ne sait pas parser → statut typé `names_only` (rouge honnête), distinct d'« introuvable ».
"""
from __future__ import annotations

import pytest

from conftest import ASTRO
from frontmap import adapters, astroparse, query, tsparse
from frontmap.adapters.primitives_astro import AstroPrimitives
from frontmap.build import build
from frontmap.config import Config

_ASTRO_READY = astroparse.available() and tsparse.available()


def _force_no_astro(monkeypatch):
    monkeypatch.setattr(astroparse, "_TRIED", True)
    monkeypatch.setattr(astroparse, "_PARSER", None)
    assert astroparse.available() is False


def _by_name():
    return {p["name"]: p for p in AstroPrimitives().extract_primitives(ASTRO, Config())}


# ── cœur pur-Python (sans parseur) ──────────────────────────────────────────────────────────────────────

def test_autodetect_astro_convention():
    d = adapters.detect(ASTRO, Config())
    assert d["primitives"] == "astro"          # auto-détecté par présence de `.astro` (pas de barrel/.tsx)
    assert d["primitives_available"] is True


def test_config_override_forces_astro():
    forced = Config(primitives_source="astro")
    assert adapters.resolve_primitives(ASTRO, forced).name == "astro"


def test_astro_primitive_names_via_filesystem_without_parser(monkeypatch):
    # contrat pivot : les NOMS viennent du filesystem (stem), aucun parseur requis → `usage` marche sans extra
    _force_no_astro(monkeypatch)
    monkeypatch.setattr(tsparse, "_PARSERS", {})
    assert AstroPrimitives().primitive_names(ASTRO, Config()) == {"Button", "Badge"}
    assert AstroPrimitives().extract_primitives(ASTRO, Config()) == []   # détail vide sans parseur


def test_astro_consumed_primitives_default_import():
    # import Astro par défaut, extension `.astro` explicite (Astro/Vite) → tolérée à la résolution
    text = "import Button from '@/components/ui/Button.astro';\n"
    got = AstroPrimitives().consumed_primitives(text, "web/src/pages/Home.tsx", Config(), {"Button", "Badge"})
    assert got == ["Button"]


# ── détail riche (grammaire astro + TS) ─────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _ASTRO_READY, reason="grammaire astro/TS absente (extras [astro]+[ts])")
def test_astro_props_variants_defaults():
    b = _by_name()["Button"]
    assert b["variants"]["variant"] == ["primary", "secondary"]   # union nommée référencée par la prop
    assert b["variants"]["size"] == ["sm", "lg"]
    assert b["defaults"] == {"variant": "primary", "size": "sm", "disabled": "false"}  # `Astro.props`
    assert {p["name"] for p in b["props"]} == {"variant", "size", "disabled"}
    assert b["file"] == "web/src/components/ui/Button.astro"

    badge = _by_name()["Badge"]
    assert badge["variants"] == {"tone": ["ok", "warn", "danger"]}
    assert "label" not in badge["variants"]                        # `label: string` non-union ≠ variante
    assert any(p["name"] == "label" and not p["optional"] for p in badge["props"])


@pytest.mark.skipif(not _ASTRO_READY, reason="grammaire astro/TS absente (extras [astro]+[ts])")
def test_check_astro_verified_is_green(tmp_path):
    build(ASTRO, tmp_path, Config())
    chk = query.check(tmp_path, ASTRO, Config())
    assert chk["primitives_status"] == "verified"
    assert chk["conventions"]["primitives"] == "astro"
    assert chk["ok"] is True
    assert chk["counts"]["primitives"] == 2


# ── honnêteté : parseur absent ⇒ rouge honnête, jamais faux-vert ─────────────────────────────────────────

def test_check_astro_names_only_is_honest_red(tmp_path, monkeypatch):
    # source `.astro` présente mais grammaire absente → catalogue NON vérifié : ni vert, ni « introuvable ».
    _force_no_astro(monkeypatch)
    res = build(ASTRO, tmp_path, Config())
    assert res["counts"]["primitives"] == 0        # détail vide (grammaire absente), mais build ne casse pas

    chk = query.check(tmp_path, ASTRO, Config())
    assert chk["primitives_status"] == "names_only"
    assert chk["ok"] is False                       # ← jamais faux-vert sur une source qu'il ne sait pas lire
    assert any("NON vérifié" in f for f in chk["findings"])
    assert not any("introuvable" in f for f in chk["findings"])   # distinct d'une source absente/mal config
