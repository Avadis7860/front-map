"""jsonl — lecture/écriture JSONL sûre (socle stdlib-pur).

Une seule implémentation, Unicode-safe : on découpe sur `\\n` UNIQUEMENT (jamais `splitlines()`, qui
casse aussi sur U+2028/2029/0085 — légitimes À L'INTÉRIEUR d'une valeur JSON). Un JSONL n'est délimité
que par `\\n`.

Vendorisé **verbatim** de `code-map` (`codemap/core/jsonl.py`).
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    """Lit un JSONL → liste d'objets. Découpe sur `\\n` seulement (Unicode-safe), ignore les lignes
    vides. `[]` si le fichier est absent. Lève `json.JSONDecodeError` sur une ligne malformée."""
    p = Path(path)
    if not p.is_file():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").split("\n") if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    """Écrit `rows` en JSONL (une ligne/objet, UTF-8, `ensure_ascii=False`, LF). Crée les parents.
    Renvoie le nombre de lignes écrites."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n
