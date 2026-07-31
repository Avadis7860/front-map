"""query — verbes de navigation (LECTURE seule). Consomme les index, ne les écrit jamais.

Jumeau de `code-map/query.py` (D7 : `build` d'abord, `query` lit). Chaque verbe renvoie un dict stable
+ `engine`. Aucune exécution d'extracteur ici — l'index doit exister (`frontmap build`).

  tokens [group]      → tokens.jsonl (filtre optionnel par groupe)
  primitives          → primitives.jsonl (résumé)
  primitive <name>    → primitives.jsonl (détail : props, variantes, defaults)
  routes              → routes.jsonl (arbre)
  where <intention>   → ranking lexical sur primitives + tokens (« quelle primitive/token pour X ? »)
  usage <name>        → usage.jsonl inversé (« qui consomme cette primitive/ce token ? »)
  consumers <file>    → usage.jsonl (ce qu'un écran consomme : primitives + tokens + route)
  check               → cohérence + fraîcheur (convention résolue, source primitives, index périmé, signaux)
"""
from __future__ import annotations

import json
from pathlib import Path

from frontmap import tsparse
from frontmap.adapters import resolve_primitives, resolve_router
from frontmap.build import MANIFEST_NAME, source_files
from frontmap.config import Config
from frontmap.core.hashing import sha_text
from frontmap.core.jsonl import read_jsonl
from frontmap.core.text import score, tokenize

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


def _consumer_ref(r: dict) -> dict:
    """Vue courte d'un consommateur (pour l'index inversé)."""
    return {"consumer": r["consumer"], "kind": r["kind"], "route": r["route"]}


def usage(index_dir: Path, name: str) -> dict:
    """Index INVERSE : « qui consomme `name` ? » — primitive (nom, insensible à la casse) ou token (exact)."""
    rows = _load(index_dir, "usage.jsonl")
    lname = name.lower()
    as_primitive = [_consumer_ref(r) for r in rows if any(p.lower() == lname for p in r["primitives"])]
    as_token = [_consumer_ref(r) for r in rows if name in r["tokens"]]
    return {"target": name, "as_primitive": as_primitive, "as_token": as_token,
            "count": len(as_primitive) + len(as_token), "engine": ENGINE}


def consumers(index_dir: Path, file: str) -> dict:
    """Ce qu'un écran consomme (primitives + tokens + route). Match par chemin rel exact ou basename."""
    rows = _load(index_dir, "usage.jsonl")
    rec = next((r for r in rows if r["consumer"] == file
                or r["consumer"].endswith(f"/{file}")
                or Path(r["consumer"]).name == file), None)
    if rec is None:
        return {"error": f"consommateur inconnu : {file}",
                "available": [r["consumer"] for r in rows], "engine": ENGINE}
    return {"consumer": rec, "engine": ENGINE}


def check(index_dir: Path, root: Path, cfg: Config) -> dict:
    """Cohérence/fraîcheur : tree-sitter présent, index frais (hash), source de primitives résolue + parsable.

    Générique par convention : la source des primitives (barrel, dossier `.tsx` ou `.astro`), sa complétude ET
    sa **parsabilité** sont vérifiées via l'adaptateur résolu → `primitives_status` (`verified`|`names_only`|
    `unavailable`) : jamais faux-vert sur une source que la convention ne sait pas parser. Les limites du
    router (routes dynamiques) remontent en `signals`."""
    index_dir, root = Path(index_dir), Path(root)
    router = resolve_router(root, cfg)
    prim = resolve_primitives(root, cfg)
    man_path = index_dir / MANIFEST_NAME
    findings: list[str] = []
    ok = True

    ts_ok = tsparse.available()
    if not ts_ok:
        findings.append("tree-sitter absent → primitives/routes vides (installer l'extra `[ts]`)")

    # Statut TYPÉ de la source de primitives (indépendant de la fraîcheur) — garantit qu'un `check` ne se lit
    # jamais faux-vert sur une source que la convention ne sait pas parser (ex. `.astro` sans `[astro]`) :
    #   verified    = source présente ET grammaire de détail chargeable → catalogue vérifié
    #   names_only  = source présente mais grammaire absente → noms connus, détail vide, NON vérifié (≠ vert)
    #   unavailable = source introuvable (convention/config qui ne pointe rien)
    if not prim.available(root, cfg):
        primitives_status = "unavailable"
    elif not prim.detail_parser_available():
        primitives_status = "names_only"
    else:
        primitives_status = "verified"

    if not man_path.is_file():
        return {"ok": False, "ts_available": ts_ok, "fresh": False,
                "conventions": {"router": router.name, "primitives": prim.name},
                "primitives_status": primitives_status,
                "findings": ["index absent — lancer `frontmap build`"], "signals": [], "engine": ENGINE}

    try:
        manifest = json.loads(man_path.read_text(encoding="utf-8"))
    except ValueError:
        manifest = {}
    cur = {f: sha_text((root / f).read_text(encoding="utf-8", errors="replace"))
           for f in source_files(root, cfg)}
    fresh = (manifest.get("file_hashes") == cur and manifest.get("ts_available") == ts_ok
             and manifest.get("conventions") == {"router": router.name, "primitives": prim.name})
    if not fresh:
        ok = False
        findings.append("index périmé (sources, dispo tree-sitter ou convention changée) — rebuild")

    # source des primitives résolue + complète + PARSABLE (cf. `primitives_status`). Un `names_only` (source
    # présente mais grammaire de détail absente) est un rouge HONNÊTE — distinct d'« introuvable » : le
    # catalogue existe mais n'a pas pu être vérifié, on ne le présente pas comme vert.
    if primitives_status == "unavailable":
        ok = False
        findings.append(f"source de primitives ({prim.name}) introuvable")
    elif primitives_status == "names_only":
        ok = False
        findings.append(f"catalogue « {prim.name} » NON vérifié : grammaire de détail absente "
                        f"(noms seuls, détail vide) — installer l'extra requis")
    for miss in prim.missing_files(root, cfg):
        ok = False
        findings.append(f"primitive « {miss} » : fichier introuvable")

    # SIGNAUX (n'invalident pas `ok`) : front-map SIGNALE, il ne juge pas (verdict = futur agent UX).
    signals: list[str] = list(router.signals(root, cfg))  # ex. routes dynamiques non résolues
    prim_rows = _load(index_dir, "primitives.jsonl")
    usage_rows = _load(index_dir, "usage.jsonl")
    if prim_rows:
        consumed = {p for r in usage_rows for p in r["primitives"]}
        dead = sorted(p["name"] for p in prim_rows if p["name"] not in consumed)
        if dead:
            signals.append(f"primitives jamais consommées : {', '.join(dead)}")

    return {"ok": ok and fresh, "ts_available": ts_ok, "fresh": fresh,
            "conventions": {"router": router.name, "primitives": prim.name},
            "primitives_status": primitives_status,
            "counts": manifest.get("counts", {}), "findings": findings, "signals": signals,
            "engine": ENGINE}
