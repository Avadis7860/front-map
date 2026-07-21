"""Permet `python -m frontmap …` (équivalent du console_script `frontmap`).

Parité avec code-map : un consommateur qui n'a pas le `.venv/bin` sur son PATH (ex. un service systemd,
ou le daemon cockpit qui invoque les cartes via `sys.executable -m <pkg>`) atteint la CLI sans dépendance
PATH. Le console_script `frontmap = frontmap.cli:main` reste la voie nominale ; ce module en est le miroir.
"""
from __future__ import annotations

from frontmap.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
