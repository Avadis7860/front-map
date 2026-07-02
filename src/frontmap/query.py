"""query — verbes de navigation (LECTURE seule). Consomme les index, ne les écrit jamais.

Jumeau de `code-map/query.py` (D7 : `build` d'abord, `query` lit). Chaque verbe renvoie un dict stable
+ `engine`. Aucune exécution d'extracteur ici — l'index doit exister (`frontmap build`).

  tokens [group]      → tokens.jsonl (filtre optionnel par groupe)
  primitives          → primitives.jsonl (résumé)
  primitive <name>    → primitives.jsonl (détail : props, variantes, defaults)
  routes              → routes.jsonl (arbre)
  where <intention>   → ranking lexical sur primitives + tokens (« quelle primitive/token pour X ? »)
  check               → cohérence + fraîcheur (barrel↔fichiers, index périmé, tree-sitter présent)
"""
from __future__ import annotations

import json
from pathlib import Path

from frontmap import tsparse
from frontmap.build import MANIFEST_NAME, source_files
from frontmap.config import Config
from frontmap.core.hashing import sha_text
from frontmap.core.jsonl import read_jsonl
from frontmap.core.text import score, tokenize
from frontmap.extractors import primitives as prim_ext

ENGINE = "frontmap-v1"


def _load(index_dir: Path, name: str) -> list[dict]:
    return read_jsonl(Path(index_dir) / name)


def tokens(index_dir: Path, group: str | None = None) -> dict:
    rows = _load(index_dir, "tokens.jsonl")
    if group:
        rows = [r for r in rows if r["group"] == group]
    return {"tokens": rows, "count": len(rows), "engine": ENGINE}


def primitives(index_dir: Path) -> dict:
    rows = _load(index_dir, "primitives.jsonl")
    summary = [{"name": r["name"], "lead": r["lead"], "variants": sorted(r["variants"]),
                "n_props": len(r["props"]), "file": r["file"]} for r in rows]
    return {"primitives": summary, "count": len(summary), "engine": ENGINE}


def primitive(index_dir: Path, name: str) -> dict:
    rows = _load(index_dir, "primitives.jsonl")
    rec = next((r for r in rows if r["name"].lower() == name.lower()), None)
    if rec is None:
        return {"error": f"primitive inconnue : {name}",
                "available": sorted(r["name"] for r in rows), "engine": ENGINE}
    return {"primitive": rec, "engine": ENGINE}


def routes(index_dir: Path) -> dict:
    rows = _load(index_dir, "routes.jsonl")
    return {"routes": rows, "count": len(rows), "engine": ENGINE}


def where(index_dir: Path, intent: str, *, top_k: int = 5) -> dict:
    """Ranking lexical borné sur primitives + tokens → candidats les plus proches de l'intention."""
    toks = tokenize(intent)
    cands: list[dict] = []
    for r in _load(index_dir, "primitives.jsonl"):
        variant_vals = " ".join(v for vals in r["variants"].values() for v in vals)
        prop_names = " ".join(p["name"] for p in r["props"])
        hay = f"{r['name']} {r['lead']} {variant_vals} {prop_names}"
        cands.append({"kind": "primitive", "name": r["name"], "file": r["file"],
                      "lead": r["lead"], "score": score(toks, r["name"], hay)})
    for r in _load(index_dir, "tokens.jsonl"):
        hay = f"{r['name']} {r['value']} {r['group']} {r['lead']}"
        cands.append({"kind": "token", "name": r["name"], "group": r["group"],
                      "value": r["value"], "score": score(toks, r["name"], hay)})
    hits = [c for c in cands if c["score"] > 0]
    hits.sort(key=lambda c: (-c["score"], c["kind"], c["name"]))
    return {"results": hits[:top_k], "engine": ENGINE}


def check(index_dir: Path, root: Path, cfg: Config) -> dict:
    """Cohérence/fraîcheur : tree-sitter présent, index frais (hash), barrel↔.tsx résolus."""
    index_dir, root = Path(index_dir), Path(root)
    man_path = index_dir / MANIFEST_NAME
    findings: list[str] = []
    ok = True

    ts_ok = tsparse.available()
    if not ts_ok:
        findings.append("tree-sitter absent → primitives/routes vides (installer l'extra `[ts]`)")

    if not man_path.is_file():
        return {"ok": False, "ts_available": ts_ok, "fresh": False,
                "findings": ["index absent — lancer `frontmap build`"], "engine": ENGINE}

    try:
        manifest = json.loads(man_path.read_text(encoding="utf-8"))
    except ValueError:
        manifest = {}
    cur = {f: sha_text((root / f).read_text(encoding="utf-8", errors="replace"))
           for f in source_files(root, cfg)}
    fresh = manifest.get("file_hashes") == cur and manifest.get("ts_available") == ts_ok
    if not fresh:
        ok = False
        findings.append("index périmé (sources modifiées ou dispo tree-sitter changée) — rebuild")

    # barrel ↔ .tsx : primitives déclarées mais fichier absent
    bpath = root / cfg.primitives_barrel
    if bpath.is_file():
        declared = prim_ext.parse_barrel(bpath.read_text(encoding="utf-8"))
        referenced = set(prim_ext.referenced_files(root, cfg.primitives_barrel))
        for entry in declared:
            tsx = prim_ext.resolve_tsx(cfg.primitives_barrel, entry["module"])
            if tsx not in referenced:
                ok = False
                findings.append(f"primitive « {entry['name']} » : fichier introuvable ({tsx})")
    else:
        ok = False
        findings.append(f"barrel de primitives introuvable : {cfg.primitives_barrel}")

    return {"ok": ok and fresh, "ts_available": ts_ok, "fresh": fresh,
            "counts": manifest.get("counts", {}), "findings": findings, "engine": ENGINE}
