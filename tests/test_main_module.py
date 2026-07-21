"""`python -m frontmap` — parité entrypoint avec le console_script (miroir de code-map).

Verrou anti-régression : un consommateur PATH-free (daemon cockpit, service systemd) invoque la CLI via
`sys.executable -m frontmap`. On prouve que le module exécutable existe et relaie `cli.main` (rc + stdout),
sans dépendre du `.venv/bin` sur le PATH.
"""
from __future__ import annotations

import subprocess
import sys

from frontmap import __version__


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "frontmap", *args],
        capture_output=True, text=True, check=False,
    )


def test_module_version_matches_package():
    """`-m frontmap --version` sort rc 0 et imprime la version du package (relaie bien `cli.main`)."""
    res = _run("--version")
    assert res.returncode == 0
    assert __version__ in res.stdout


def test_module_help_lists_verbs():
    """`-m frontmap --help` expose les verbes de la CLI (le module est bien le miroir du console_script)."""
    res = _run("--help")
    assert res.returncode == 0
    assert "tokens" in res.stdout and "routes" in res.stdout
