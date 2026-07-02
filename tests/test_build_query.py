"""build + query — pipeline bout-en-bout : matérialisation, fraîcheur, verbes de lecture."""
from __future__ import annotations

import pytest

from conftest import FIXTURES
from frontmap import query, tsparse
from frontmap.build import build

_TS = tsparse.available()


def test_build_writes_indexes_and_skips_when_fresh(tmp_path, cfg):
    res1 = build(FIXTURES, tmp_path, cfg)
    assert res1["skipped"] is False
    assert res1["counts"]["tokens"] > 0
    for name in ("tokens.jsonl", "primitives.jsonl", "routes.jsonl", "frontmap.manifest.json"):
        assert (tmp_path / name).exists()

    # 2e build sur sources inchangées → skip idempotent (fraîcheur par hash)
    assert build(FIXTURES, tmp_path, cfg)["skipped"] is True
    # --force ré-exécute
    assert build(FIXTURES, tmp_path, cfg, force=True)["skipped"] is False


def test_query_tokens_by_group(tmp_path, cfg):
    build(FIXTURES, tmp_path, cfg)
    assert query.tokens(tmp_path, "accent")["count"] == 2
    assert query.tokens(tmp_path, "status")["count"] == 2
    assert query.tokens(tmp_path)["count"] > 4


@pytest.mark.skipif(not _TS, reason="tree-sitter absent (extra [ts])")
def test_query_primitive_detail_and_routes(tmp_path, cfg):
    build(FIXTURES, tmp_path, cfg)
    assert query.primitives(tmp_path)["count"] == 2
    b = query.primitive(tmp_path, "button")["primitive"]   # insensible à la casse
    assert b["defaults"]["size"] == "md"
    assert query.primitive(tmp_path, "Nope")["error"]
    r = query.routes(tmp_path)["routes"]
    assert any(x["full_path"] == "/$project/gate" for x in r)


@pytest.mark.skipif(not _TS, reason="tree-sitter absent (extra [ts])")
def test_where_ranks_badge_for_status_intent(tmp_path, cfg):
    build(FIXTURES, tmp_path, cfg)
    results = query.where(tmp_path, "badge de statut")["results"]
    assert results and results[0]["name"] == "Badge"


@pytest.mark.skipif(not _TS, reason="tree-sitter absent (extra [ts])")
def test_check_ok_after_build(tmp_path, cfg):
    build(FIXTURES, tmp_path, cfg)
    chk = query.check(tmp_path, FIXTURES, cfg)
    assert chk["fresh"] is True
    assert chk["ok"] is True
    assert chk["ts_available"] is True
