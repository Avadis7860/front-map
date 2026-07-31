"""dégradation gracieuse — deux axes.

1. **tree-sitter absent** : primitives/routes vides, tokens+usage OK, sans exception.
2. **index absent** : les verbes de LECTURE rendent un message actionnable (« lance `frontmap build` »)
   au lieu d'un vide TROMPEUR (`{"tokens": [], "count": 0}` ne distinguait pas « aucun token » de « aucun
   index »), et **empruntent** l'index du répertoire de travail principal quand on les interroge depuis une
   worktree liée — les index dérivés ne sont pas versionnés, `git worktree add` ne les emporte donc pas, et
   c'est précisément là que tout le travail se fait.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from conftest import FIXTURES
from frontmap import cli, query, tsparse
from frontmap.adapters.primitives_barrel import BarrelPrimitives
from frontmap.adapters.router_tanstack import TanstackRouter
from frontmap.build import MANIFEST_NAME, build
from frontmap.config import INDEX_DIRNAME, Config
from frontmap.core import roots


def _force_no_treesitter(monkeypatch):
    # `_parsers()` renvoie `_PARSERS or None` → un dict vide simule tree-sitter indisponible.
    monkeypatch.setattr(tsparse, "_PARSERS", {})
    assert tsparse.available() is False


def test_primitives_and_routes_empty_without_treesitter(monkeypatch):
    _force_no_treesitter(monkeypatch)
    assert BarrelPrimitives().extract_primitives(FIXTURES, Config()) == []
    assert TanstackRouter().extract_routes(FIXTURES, Config()) == []


def test_build_still_produces_tokens_and_check_flags_absence(tmp_path, cfg, monkeypatch):
    _force_no_treesitter(monkeypatch)
    res = build(FIXTURES, tmp_path, cfg)
    assert res["skipped"] is False
    assert res["counts"]["tokens"] > 0        # tokens (CSS pur) toujours produits
    assert res["counts"]["primitives"] == 0
    assert res["counts"]["routes"] == 0

    chk = query.check(tmp_path, FIXTURES, cfg)
    assert chk["ts_available"] is False
    assert any("tree-sitter" in f for f in chk["findings"])


def test_usage_still_works_without_treesitter(tmp_path, cfg, monkeypatch):
    # usage est PUR-Python (barrel + imports en regex) → produit même sans tree-sitter ; seul le lien
    # route se dégrade à None (routes vide).
    _force_no_treesitter(monkeypatch)
    res = build(FIXTURES, tmp_path, cfg)
    assert res["counts"]["usage"] > 0
    assert query.usage(tmp_path, "Button")["count"] >= 2   # Home + Workspace

    home = query.consumers(tmp_path, "Home.tsx")["consumer"]
    assert "Button" in home["primitives"]
    assert home["route"] is None                            # non résolu sans tree-sitter


# --- index absent : garde honnête (précondition de l'emprunt) ----------------------------------------

READ_CMDS = [
    ["tokens"],
    ["primitives"],
    ["primitive", "Button"],
    ["routes"],
    ["where", "bouton"],
    ["usage", "Button"],
    ["consumers", "Home.tsx"],
]


@pytest.mark.parametrize("argv", READ_CMDS, ids=[c[0] for c in READ_CMDS])
def test_read_verbs_degrade_when_index_absent(tmp_path: Path, capsys, argv):
    """AVANT : `{"tokens": [], "count": 0}` — un vide qui a l'air d'une réponse. On ne pouvait pas
    distinguer « ce repo n'a aucun token » de « personne n'a bâti l'index »."""
    rc = cli.main([*argv, "--root", str(tmp_path)])       # tmp_path n'a AUCUN .frontmap/
    out = json.loads(capsys.readouterr().out)
    assert rc == 0                                        # rc inchangé : ces verbes sortaient déjà 0
    assert out["ok"] is False
    assert "frontmap build" in out["reason"]              # actionnable : nomme la commande de sortie


def test_check_keeps_its_own_absent_verdict(tmp_path: Path, capsys):
    """`check` n'est PAS guardé : il diagnostique l'absence lui-même, avec ses champs propres
    (`ts_available`, `conventions`, `primitives_status`) qu'une garde générique écraserait."""
    rc = cli.main(["check", "--root", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1 and out["ok"] is False
    assert "frontmap build" in out["findings"][0]
    assert "primitives_status" in out                     # verdict typé conservé, pas remplacé


def test_read_verbs_work_once_index_built(tmp_path: Path, capsys, cfg):
    """Contrôle positif : la garde est non intrusive dès que l'index existe."""
    build(FIXTURES, tmp_path / INDEX_DIRNAME, cfg)
    rc = cli.main(["tokens", "--root", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0 and out["count"] > 0
    assert "ok" not in out                                # la sortie nominale n'a PAS bougé


# --- emprunt d'index en worktree liée ---------------------------------------------------------------

def _fake_worktree(tmp_path: Path, name: str = "essai") -> tuple[Path, Path]:
    """Fabrique le layout d'une worktree LIÉE **à la main**, sans aucun binaire git :

        principal/.git/worktrees/<name>/commondir   contient `../..`  → principal/.git
        detachee/.git                               contient `gitdir: <abs>/principal/.git/worktrees/<name>`

    C'est exactement ce qu'écrit `git worktree add` — le tester ainsi garde le cœur stdlib-pur (les tests
    ne dépendent ni de la présence de git, ni de sa version)."""
    principal = tmp_path / "principal"
    detachee = tmp_path / "detachee"
    gitdir = principal / ".git" / "worktrees" / name
    gitdir.mkdir(parents=True)
    (gitdir / "commondir").write_text("../..\n", encoding="utf-8")
    detachee.mkdir()
    (detachee / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    return principal, detachee


def test_main_worktree_root_resolves_linked_worktree(tmp_path: Path):
    principal, detachee = _fake_worktree(tmp_path)
    assert roots.main_worktree_root(detachee) == principal.resolve()


@pytest.mark.parametrize("wreck", ["repo-normal", "gitfile-illisible", "commondir-absent"], ids=str)
def test_main_worktree_root_is_none_on_anything_unexpected(tmp_path: Path, wreck: str):
    """Fail-soft : aucune racine DEVINÉE. La moindre déviation rend None (l'appelant garde son
    comportement d'origine), plutôt qu'un chemin plausible mais faux."""
    if wreck == "repo-normal":
        (tmp_path / ".git").mkdir()                       # repo classique : `.git` est un RÉPERTOIRE
    elif wreck == "gitfile-illisible":
        (tmp_path / ".git").write_text("ceci n'est pas un gitfile\n", encoding="utf-8")
    else:
        gitdir = tmp_path / "ailleurs"                    # gitfile valide mais sans `commondir`
        gitdir.mkdir()
        (tmp_path / ".git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    assert roots.main_worktree_root(tmp_path) is None


def test_read_verb_borrows_main_index_from_worktree(tmp_path: Path, capsys, cfg):
    """LE TROU REFERMÉ : dans une worktree sans index (cas par défaut, les index sont gitignorés), un verbe
    de lecture répond en empruntant l'index du principal — et l'annonce sur stderr."""
    principal, detachee = _fake_worktree(tmp_path)
    build(FIXTURES, principal / INDEX_DIRNAME, cfg)
    assert not (detachee / INDEX_DIRNAME).exists()        # la worktree n'a hérité de rien : c'est le défaut

    rc = cli.main(["tokens", "--root", str(detachee)])
    cap = capsys.readouterr()
    assert rc == 0
    assert json.loads(cap.out)["count"] > 0               # avant : `ok:false` → grep du front à l'aveugle
    assert "emprunté" in cap.err and str(principal) in cap.err   # fraîcheur annoncée, jamais prétendue
    assert "emprunté" not in cap.out                      # le JSON consommé par un agent n'a PAS bougé


def test_borrow_warning_is_emitted_once(tmp_path: Path, capsys, cfg):
    """`main()` résout deux fois (garde `needs_index`, puis le handler) : sans la garde de premier appel,
    l'avertissement sortirait en double."""
    principal, detachee = _fake_worktree(tmp_path)
    build(FIXTURES, principal / INDEX_DIRNAME, cfg)

    cli.main(["tokens", "--root", str(detachee)])
    assert capsys.readouterr().err.count("emprunté") == 1


def test_build_never_borrows_in_worktree(tmp_path: Path, capsys, cfg):
    """L'anti-régression qui compte : un verbe qui ÉCRIT n'emprunte jamais — il écrirait l'index de la
    feature dans le répertoire principal (corruption silencieuse de celui de `dev`). Le critère est
    « le verbe écrit-il dans `index_dir` ? », jamais son nom."""
    principal, detachee = _fake_worktree(tmp_path)
    build(FIXTURES, principal / INDEX_DIRNAME, cfg)
    avant = (principal / INDEX_DIRNAME / MANIFEST_NAME).read_bytes()
    shutil.copytree(FIXTURES / "web", detachee / "web")   # la worktree a bien un front à indexer

    rc = cli.main(["build", "--root", str(detachee)])
    capsys.readouterr()
    assert rc == 0
    assert (detachee / INDEX_DIRNAME / MANIFEST_NAME).is_file()                  # écrit CHEZ ELLE
    assert (principal / INDEX_DIRNAME / MANIFEST_NAME).read_bytes() == avant     # le principal intact


def test_check_never_borrows_in_worktree(tmp_path: Path, capsys, cfg):
    """`check` n'emprunte pas non plus : il répondrait vert sur l'index d'un AUTRE répertoire. Sur une
    worktree sans index, le verdict honnête reste « index absent »."""
    principal, detachee = _fake_worktree(tmp_path)
    build(FIXTURES, principal / INDEX_DIRNAME, cfg)

    rc = cli.main(["check", "--root", str(detachee)])
    cap = capsys.readouterr()
    assert rc == 1 and json.loads(cap.out)["ok"] is False
    assert cap.err == ""                                  # aucun emprunt, donc aucun avertissement


def test_no_borrow_when_main_has_no_index_either(tmp_path: Path, capsys):
    """Rien à emprunter ⇒ le message honnête, mot pour mot. On ne remplace pas un silence par un mensonge."""
    _, detachee = _fake_worktree(tmp_path)
    rc = cli.main(["tokens", "--root", str(detachee)])
    cap = capsys.readouterr()
    assert rc == 0
    assert json.loads(cap.out)["ok"] is False
    assert "frontmap build" in json.loads(cap.out)["reason"]
    assert cap.err == ""                                  # aucun avertissement : rien n'a été emprunté
