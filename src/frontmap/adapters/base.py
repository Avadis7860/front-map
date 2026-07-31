"""base — contrats d'adaptateurs de CONVENTION (schéma de sortie figé, adaptateur pluggable).

Jumeau des *engines* de code-map (`engines/base.py`), transposé au front : là où code-map varie par
**langage**, front-map varie par **convention** de deux axes ORTHOGONAUX — le *router* (comment les routes
sont déclarées) et les *primitives* (comment le catalogue du design-system est exposé). Chaque axe a son
Protocol ; un projet compose un adaptateur de chaque (ex. TanStack + dir-scan). Le **schéma des lignes
JSONL est FIGÉ** (comme le `Symbol` de code-map) : les adaptateurs le REMPLISSENT, quelle que soit la
convention → zéro rupture pour les consommateurs (CLI, futur agent critique).

Contrat best-effort commun : les méthodes d'extraction renvoient `[]`/`set()` si la source est absente ou
si tree-sitter manque — **jamais d'exception** (un dispatch ne doit pas casser).
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, TypedDict

from frontmap.config import Config


class RouteRow(TypedDict):
    """Ligne de `routes.jsonl` (schéma figé). `var` = identifiant/clé de la route ; `parent` = `var` du
    parent (None si racine) ; `full_path` = chemin chaîné ; `is_root` = nœud racine de l'arbre."""

    var: str
    path: str | None
    full_path: str
    component: str | None
    parent: str | None
    is_root: bool
    file: str
    line: int


class PrimitiveRow(TypedDict):
    """Ligne de `primitives.jsonl` (schéma figé). `props`/`variants`/`defaults` sont best-effort tree-sitter
    (peuvent être vides sans l'extra `[ts]` ou pour une forme de props non modélisée)."""

    name: str
    file: str
    line: int
    props: list[dict]
    variants: dict[str, list[str]]
    defaults: dict[str, str]
    lead: str


class RouterAdapter(Protocol):
    """Extraction de l'arbre des routes pour UNE convention de routing.

    `name` : clé de convention (`tanstack` | `react-router`). `extract_routes` remplit `RouteRow` ;
    `referenced_files` liste les sources à hasher ; `signals` remonte les limites connues (ex. routes
    générées dynamiquement, non résolues)."""

    name: str

    def available(self, root: Path, cfg: Config) -> bool: ...
    def extract_routes(self, root: Path, cfg: Config) -> list[RouteRow]: ...
    def referenced_files(self, root: Path, cfg: Config) -> list[str]: ...
    def signals(self, root: Path, cfg: Config) -> list[str]: ...


class PrimitivesAdapter(Protocol):
    """Catalogue des primitives + détection de leur consommation, pour UNE convention d'exposition.

    `name` : clé (`barrel` | `dir-scan` | `astro`). `primitive_names` est le **contrat pivot** (regex/
    filesystem, SANS tree-sitter → `usage` marche sans les extras). `consumed_primitives` encapsule la façon
    dont CETTE convention importe une primitive (nommé depuis un barrel, ou défaut depuis un fichier).
    `ui_dir` = dossier des primitives (exclu du scan des consommateurs). `missing_files` = primitives
    déclarées dont le fichier manque (pour `check` ; vide quand la source EST le fichier, cf. dir-scan/astro).
    `detail_parser_available` = la grammaire tree-sitter dont CETTE convention a besoin pour le détail riche
    est-elle chargeable ? (`[ts]` pour barrel/dir-scan ; `[astro]` + `[ts]` pour astro) → `check` distingue
    « vérifié » de « noms seuls » sans jamais se lire faux-vert sur une source qu'il ne sait pas parser."""

    name: str

    def available(self, root: Path, cfg: Config) -> bool: ...
    def primitive_names(self, root: Path, cfg: Config) -> set[str]: ...
    def referenced_files(self, root: Path, cfg: Config) -> list[str]: ...
    def ui_dir(self, root: Path, cfg: Config) -> str: ...
    def detail_parser_available(self) -> bool: ...
    def consumed_primitives(self, text: str, importer_rel: str, cfg: Config,
                            names: set[str]) -> list[str]: ...
    def extract_primitives(self, root: Path, cfg: Config) -> list[PrimitiveRow]: ...
    def missing_files(self, root: Path, cfg: Config) -> list[str]: ...
