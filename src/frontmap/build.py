"""build — orchestre les 3 extracteurs, écrit les index JSONL, gère la **fraîcheur par hash**.

`build` écrit / `query` lit (invariant jumeau de code-map) : cette couche est la SEULE qui exécute les
extracteurs et matérialise `tokens.jsonl` / `primitives.jsonl` / `routes.jsonl` + un manifest de fraîcheur.
Idempotent : si les hash des sources ET la disponibilité de tree-sitter sont inchangés, on **skip** (pas de
ré-écriture). Hash de **contenu** (jamais mtime → pas de faux-rouge). La signature `ts_available` invalide
la réutilisation quand tree-sitter apparaît/disparaît (sinon un index TSX vide resterait vide une fois la
dépendance installée — même garde que code-map).
"""
from __future__ import annotations

import json
from pathlib import Path

from frontmap import tsparse
from frontmap.config import Config
from frontmap.core.hashing import sha_text
from frontmap.core.jsonl import write_jsonl
from frontmap.extractors import primitives, routes, tokens

CONTRACT_VERSION = "frontmap-index-v1"
MANIFEST_NAME = "frontmap.manifest.json"


def source_files(root: Path, cfg: Config) -> list[str]:
    """Fichiers sources consommés par les 3 extracteurs (dédup, ordre stable) — base du hash."""
    root = Path(root)
    files: list[str] = []
    if (root / cfg.tokens_file).is_file():
        files.append(cfg.tokens_file)
    files.extend(primitives.referenced_files(root, cfg.primitives_barrel))
    if (root / cfg.router_file).is_file():
        files.append(cfg.router_file)
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
    """(Re)construit les 3 index sous `index_dir`. Skip idempotent si sources + dispo TS inchangées."""
    root, index_dir = Path(root), Path(index_dir)
    files = source_files(root, cfg)
    hashes = _hashes(root, files)
    ts_avail = tsparse.available()
    man_path = index_dir / MANIFEST_NAME

    if not force and man_path.is_file():
        try:
            prev = json.loads(man_path.read_text(encoding="utf-8"))
        except ValueError:
            prev = {}
        if prev.get("file_hashes") == hashes and prev.get("ts_available") == ts_avail:
            return {"skipped": True, "reason": "sources inchangées",
                    "counts": prev.get("counts", {}), "index": str(index_dir)}

    tok = tokens.extract_tokens(_read(root, cfg.tokens_file), cfg.tokens_file)
    prim = primitives.extract_primitives(root, cfg.primitives_barrel)
    rts = routes.extract_routes(root, cfg.router_file)

    index_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(index_dir / "tokens.jsonl", tok)
    write_jsonl(index_dir / "primitives.jsonl", prim)
    write_jsonl(index_dir / "routes.jsonl", rts)

    counts = {"tokens": len(tok), "primitives": len(prim), "routes": len(rts)}
    manifest = {
        "contract_version": CONTRACT_VERSION,
        "ts_available": ts_avail,
        "counts": counts,
        "file_hashes": hashes,
    }
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    return {"skipped": False, "counts": counts, "ts_available": ts_avail, "index": str(index_dir)}
