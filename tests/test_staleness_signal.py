"""Tests du signal de péremption aux verbes de LECTURE — « ce catalogue a-t-il prévenu ? ».

Distinct de `check`, qui sait rougir *quand on le tape*. Le défaut mesuré le 2026-08-01 est ailleurs :
personne ne le tape avant une question. Les agents lisent par `where`/`primitives`/`tokens`, et ces verbes
servaient leur catalogue avec l'autorité d'un index et **0 octet sur stderr**.

SPÉCIMEN FONDATEUR, relevé sur le cockpit (index gelé au 07-25, `web/` bougé le 07-31) : `FileDrop.tsx`
existait, exporté par le barrel et consommé par un écran ; `frontmap primitives` en listait 16 sans lui, et
`frontmap where "zone de dépôt de fichier"` rendait `{"results": []}`, rc 0, stderr vide. Une session qui
applique « ne réinvente pas un primitive existant » recevait un **vide confiant** et réécrivait le
composant. C'est ce cas-là, et pas la simple dérive de lignes, que `test_une_primitive_neuve_*` fige.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from conftest import FIXTURES
from frontmap.build import build
from frontmap.cli import main
from frontmap.config import Config


def _projet(tmp_path: Path) -> Path:
    """Une copie MUTABLE de la fixture (les fixtures partagées sont en lecture seule) + son index bâti."""
    root = tmp_path / "app"
    shutil.copytree(FIXTURES, root)
    build(root, root / ".frontmap", Config())
    return root


def _exporte(root: Path, *noms: str) -> None:
    """Écrit des primitives ET les exporte du barrel.

    Le second geste est load-bearing : le périmètre indexé de `frontmap` n'est PAS un glob du repo, ce sont
    les fichiers **référencés** (barrel + router + consommateurs, cf. `build.source_files`). Un `.tsx` que
    personne n'exporte n'appartient pas au design-system et ne périme donc rien — frontière délibérée,
    prouvée par `test_un_fichier_hors_perimetre_ne_perime_rien`.
    """
    ui = root / "web" / "src" / "components" / "ui"
    barrel = ui / "index.ts"
    lignes = barrel.read_text(encoding="utf-8")
    for nom in noms:
        (ui / f"{nom}.tsx").write_text(
            f"export function {nom}() {{\n  return <div>zone de dépôt de fichier</div>;\n}}\n",
            encoding="utf-8")
        lignes += f'export {{ {nom} }} from "./{nom}";\n'
    barrel.write_text(lignes, encoding="utf-8")


def test_un_catalogue_frais_ne_dit_rien(tmp_path: Path, capsys):
    """Le silence est le cas normal — un signal qui parle tout le temps devient du bruit qu'on fait taire."""
    root = _projet(tmp_path)
    main(["primitives", "--root", str(root)])
    assert capsys.readouterr().err == ""


def test_une_primitive_neuve_rend_le_catalogue_PERIME_et_ca_se_dit(tmp_path: Path, capsys):
    """LE test du spécimen `FileDrop` : le fichier existe, le barrel l'exporte, le catalogue l'ignore.
    Sans le signal, la réponse est un vide confiant — et le composant se réécrit."""
    root = _projet(tmp_path)
    _exporte(root, "FileDrop")
    main(["primitives", "--root", str(root)])
    cap = capsys.readouterr()
    noms = [p["name"] for p in json.loads(cap.out)["primitives"]]
    assert "FileDrop" not in noms, "le test ne prouve rien si l'index connaît déjà la primitive"
    assert "index périmé" in cap.err
    assert "∅" in cap.err and "FileDrop.tsx" in cap.err
    assert "frontmap build" in cap.err


def test_un_where_qui_rend_VIDE_avertit_aussi(tmp_path: Path, capsys):
    """Le vide est la réponse la plus dangereuse : rien à inspecter, aucune raison de douter."""
    root = _projet(tmp_path)
    _exporte(root, "FileDrop")
    main(["where", "zone de depot de fichier", "--root", str(root)])
    cap = capsys.readouterr()
    assert json.loads(cap.out)["results"] == []
    assert "index périmé" in cap.err


def test_stdout_reste_strictement_le_contrat_json(tmp_path: Path, capsys):
    """Le canal est la décision porteuse : un consommateur qui parse la sortie ne doit pas voir apparaître
    un champ pour une information d'ergonomie CLI."""
    root = _projet(tmp_path)
    (root / "web" / "src" / "components" / "ui" / "Button.tsx").write_text(
        "export function Button() {\n  return null;\n}\n", encoding="utf-8")
    main(["tokens", "--root", str(root)])
    cap = capsys.readouterr()
    assert cap.err, "le test ne prouve rien si l'index n'est pas périmé"
    payload = json.loads(cap.out)                      # lève si stderr avait fui dans stdout
    assert "stale" not in payload and "fresh" not in payload


def test_un_fichier_MODIFIE_et_un_fichier_NEUF_sont_distingues(tmp_path: Path, capsys):
    """`∅` (jamais indexé) ≠ `≠` (modifié) : le premier est un SILENCE (absent de toute réponse), le second
    un FAUX (ce qui est servi pour lui est périmé). Les aplatir cacherait le plus dangereux des deux."""
    root = _projet(tmp_path)
    _exporte(root, "Neuve")
    (root / "web" / "src" / "components" / "ui" / "Button.tsx").write_text(
        "export function Button() {\n  return 1;\n}\n", encoding="utf-8")
    main(["primitives", "--root", str(root)])
    err = capsys.readouterr().err
    assert "∅" in err and "Neuve.tsx" in err
    assert "≠" in err and "Button.tsx" in err


def test_un_fichier_hors_perimetre_ne_perime_rien(tmp_path: Path, capsys):
    """FRONTIÈRE, et pas un trou : le périmètre indexé n'est pas un glob du repo mais les fichiers
    RÉFÉRENCÉS (barrel, router, consommateurs). Un `.tsx` que personne n'exporte n'appartient pas au
    design-system — le compter périmerait l'index à chaque brouillon, et une garde qui s'allume sur ce qui
    est normal finit par se faire taire."""
    root = _projet(tmp_path)
    (root / "web" / "src" / "components" / "ui" / "Brouillon.tsx").write_text(
        "export function Brouillon() {\n  return null;\n}\n", encoding="utf-8")
    main(["primitives", "--root", str(root)])
    assert capsys.readouterr().err == ""


def test_le_cap_de_la_liste_s_annonce(tmp_path: Path, capsys):
    """Invariant maison : jamais de cap silencieux. 7 fichiers neufs, 5 nommés, le reste COMPTÉ."""
    root = _projet(tmp_path)
    _exporte(root, *[f"N{i}" for i in range(7)])
    main(["primitives", "--root", str(root)])
    err = capsys.readouterr().err
    assert "7 jamais indexé(s)" in err
    assert "+2 autre(s)" in err


def test_l_avertissement_sort_UNE_fois_par_invocation(tmp_path: Path, capsys):
    """Point d'appel unique dans `main()`, pas un câblage verbe par verbe."""
    root = _projet(tmp_path)
    _exporte(root, "Neuve")
    main(["primitives", "--root", str(root)])
    assert capsys.readouterr().err.count("index périmé") == 1


def test_un_index_EMPRUNTE_ne_declenche_pas_le_signal(tmp_path: Path, monkeypatch, capsys):
    """Une worktree lit l'index du principal : hacher SON front contre CE manifest rendrait tout le diff de
    la feature « périmé », par-dessus un `⚠ index emprunté` qui dit déjà exactement cela."""
    principal = _projet(tmp_path)
    worktree = tmp_path / "wt"
    shutil.copytree(FIXTURES, worktree)
    _exporte(worktree, "Neuve")          # la worktree a du front que l'index du principal ignore
    monkeypatch.setattr("frontmap.core.roots.main_worktree_root", lambda _root: principal)
    main(["primitives", "--root", str(worktree)])
    err = capsys.readouterr().err
    assert "index emprunté" in err
    assert "index périmé" not in err


def test_index_absent_dit_absent_et_pas_perime(tmp_path: Path, capsys):
    """Deux verdicts distincts : « pas d'index » est déjà rendu sur stdout par la garde `needs_index`."""
    root = tmp_path / "app"
    shutil.copytree(FIXTURES, root)
    main(["primitives", "--root", str(root)])
    cap = capsys.readouterr()
    assert "index absent" in json.loads(cap.out)["reason"]
    assert "index périmé" not in cap.err


def test_freshness_est_la_source_unique_de_check(tmp_path: Path):
    """`check` est le FORMATEUR de `freshness()`. Deux calculateurs finiraient par diverger — et c'est
    l'écart entre eux qui deviendrait le prochain faux-vert."""
    from frontmap import query
    root = _projet(tmp_path)
    idx, cfg = root / ".frontmap", Config()
    assert query.freshness(idx, root, cfg)["ok"] is True
    assert query.check(idx, root, cfg)["fresh"] is True
    (root / "web" / "src" / "components" / "ui" / "Button.tsx").write_text(
        "export function Button() {\n  return 2;\n}\n", encoding="utf-8")
    assert query.freshness(idx, root, cfg)["ok"] is False
    assert query.check(idx, root, cfg)["fresh"] is False
