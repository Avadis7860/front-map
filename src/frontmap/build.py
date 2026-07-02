"""build — orchestre les extracteurs (via adaptateurs de convention), écrit les index JSONL, gère la
**fraîcheur par hash**.

`build` écrit / `query` lit (invariant jumeau de code-map). Les axes variables (router, primitives) passent
par des ADAPTATEURS résolus depuis la config (auto-détection ou override) → front-map indexe n'importe
quelle convention. Idempotent : skip si hash des sources ET dispo tree-sitter ET **convention retenue**
inchangés (une convention qui change doit reparser — même garde que code-map sur `available`).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from frontmap import tsparse
from frontmap.adapters import resolve_primitives, resolve_router
from frontmap.config import Config
from frontmap.core.hashing import sha_text
from frontmap.core.jsonl import write_jsonl
from frontmap.extractors import tokens, usage

CONTRACT_VERSION = "frontmap-index-v1"
MANIFEST_NAME = "frontmap.manifest.json"


def source_files(root: Path, cfg: Config) -> list[str]:
    """Fichiers sources consommés par les extracteurs (dédup, ordre stable) — base du hash. Passe par les
    adaptateurs résolus (le dossier de primitives scanné diffère selon la convention)."""
    root = Path(root)
    router = resolve_router(root, cfg)
    prim = resolve_primitives(root, cfg)
    files: list[str] = []
    if (root / cfg.tokens_file).is_file():
        files.append(cfg.tokens_file)
    files.extend(prim.referenced_files(root, cfg))
    files.extend(router.referenced_files(root, cfg))
    files.extend(usage.consumer_files(root, cfg, prim.ui_dir(root, cfg)))
    seen: set[str] = set()
    out: list[str] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def _hashes(root: Path, files: list[str]) -> dict[str, str]:
    root = Path(root)
    return {f: sha_text((root / f).read_text(encoding="utf-8", errors="replace")) for f in files}


def _read(root: Path, rel: str) -> str:
    p = Path(root) / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def build(root: Path, index_dir: Path, cfg: Config, *, force: bool = False) -> dict:
    """(Re)construit les index sous `index_dir`. Skip idempotent si sources + TS + convention inchangés."""
    root, index_dir = Path(root), Path(index_dir)
    router = resolve_router(root, cfg)
    prim = resolve_primitives(root, cfg)
    conventions = {"router": router.name, "primitives": prim.name}
    files = source_files(root, cfg)
    hashes = _hashes(root, files)
    ts_avail = tsparse.available()
    man_path = index_dir / MANIFEST_NAME

    if not force and man_path.is_file():
        try:
            prev = json.loads(man_path.read_text(encoding="utf-8"))
        except ValueError:
            prev = {}
        if (prev.get("file_hashes") == hashes and prev.get("ts_available") == ts_avail
                and prev.get("conventions") == conventions):
            return {"skipped": True, "reason": "sources inchangées",
                    "counts": prev.get("counts", {}), "conventions": conventions, "index": str(index_dir)}

    tok = tokens.extract_tokens(_read(root, cfg.tokens_file), cfg.tokens_file)
    prim_rows = prim.extract_primitives(root, cfg)
    rts = router.extract_routes(root, cfg)
    # Vocabulaire connu pour l'index inverse. Noms de primitives via l'adaptateur (regex/filesystem, SANS
    # tree-sitter) et NON via `prim_rows` : sans tree-sitter `prim_rows` est vide, mais la liste des noms
    # reste connue — `usage` doit rester exploitable sans l'extra `[ts]`.
    usg = usage.extract_usage(root, cfg, prim, prim.primitive_names(root, cfg),
                              {t["name"] for t in tok}, rts)

    index_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(index_dir / "tokens.jsonl", tok)
    write_jsonl(index_dir / "primitives.jsonl", cast("list[dict]", prim_rows))
    write_jsonl(index_dir / "routes.jsonl", cast("list[dict]", rts))
    write_jsonl(index_dir / "usage.jsonl", usg)

    counts = {"tokens": len(tok), "primitives": len(prim_rows), "routes": len(rts), "usage": len(usg)}
    manifest = {
        "contract_version": CONTRACT_VERSION,
        "ts_available": ts_avail,
        "conventions": conventions,
        "counts": counts,
        "file_hashes": hashes,
    }
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    return {"skipped": False, "counts": counts, "ts_available": ts_avail,
            "conventions": conventions, "index": str(index_dir)}
