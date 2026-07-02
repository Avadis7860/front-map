"""Fixtures partagées : racine du mini web/ d'échantillon + config par défaut."""
from __future__ import annotations

from pathlib import Path

import pytest

from frontmap.config import Config

FIXTURES = Path(__file__).parent / "fixtures"          # projet 1 : TanStack + barrel (convention cockpit)
RR = Path(__file__).parent / "fixtures_rr"             # projet 2 : react-router + dir-scan
BARREL = "web/src/components/ui/index.ts"
TOKENS = "web/src/index.css"
ROUTER = "web/src/router.tsx"


@pytest.fixture
def fixtures_root() -> Path:
    return FIXTURES


@pytest.fixture
def cfg() -> Config:
    return Config()  # défauts = conventions cockpit, qui matchent la structure de la fixture


@pytest.fixture
def rr_root() -> Path:
    return RR


@pytest.fixture
def cfg_rr() -> Config:
    return Config()  # mêmes défauts ; l'auto-détection résout react-router + dir-scan sur l'arbre rr-app
