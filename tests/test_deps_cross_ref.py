"""Tests for use-package cross-referencing in locate_package_metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.deps import locate_package_metadata

if TYPE_CHECKING:
    from pathlib import Path


def _make_header_el(path: Path) -> None:
    """Write a minimal .el file with a Package-Requires: header."""
    path.write_text(
        ';; Package-Requires: ((emacs "25.1"))\n',
        encoding="utf-8",
    )


def test_cross_ref_selects_matching_candidate(tmp_path: Path) -> None:
    """Two candidates (dash, dash-functional); init declares dash."""
    _make_header_el(tmp_path / "dash.el")
    _make_header_el(tmp_path / "dash-functional.el")
    inits = tmp_path / "inits"
    inits.mkdir()
    init = inits / "soma-dash-init.el"
    init.write_text("(use-package dash\n", encoding="utf-8")
    _, name = locate_package_metadata(
        tmp_path, init_file="soma-dash-init.el", inits_dir=inits,
    )
    assert name == "dash"


def test_cross_ref_no_match_falls_back(tmp_path: Path) -> None:
    """One candidate (evil-test-helpers); init declares evil -- no match, fallback."""
    _make_header_el(tmp_path / "evil-test-helpers.el")
    inits = tmp_path / "inits"
    inits.mkdir()
    init = inits / "soma-evil-init.el"
    init.write_text("(use-package evil\n", encoding="utf-8")
    _, name = locate_package_metadata(
        tmp_path, init_file="soma-evil-init.el", inits_dir=inits,
    )
    assert name == "evil-test-helpers"


def test_cross_ref_three_candidates(tmp_path: Path) -> None:
    """Three candidates; init declares dired-hacks-utils -- auto-selects it."""
    for n in ("dired-avfs", "dired-hacks-utils", "dired-filter"):
        _make_header_el(tmp_path / f"{n}.el")
    inits = tmp_path / "inits"
    inits.mkdir()
    init = inits / "soma-dired-hacks-utils-init.el"
    init.write_text("(use-package dired-hacks-utils\n", encoding="utf-8")
    _, name = locate_package_metadata(
        tmp_path, init_file="soma-dired-hacks-utils-init.el", inits_dir=inits,
    )
    assert name == "dired-hacks-utils"


def test_cross_ref_inits_dir_none(tmp_path: Path) -> None:
    """inits_dir=None: no cross-referencing, existing behavior unchanged."""
    _make_header_el(tmp_path / "dash.el")
    _, name = locate_package_metadata(tmp_path, inits_dir=None)
    assert name == "dash"


def test_cross_ref_init_file_missing(tmp_path: Path) -> None:
    """Init file not on disk: fallback to existing behavior."""
    _make_header_el(tmp_path / "dash.el")
    _make_header_el(tmp_path / "dash-functional.el")
    inits = tmp_path / "inits"
    inits.mkdir()
    _, name = locate_package_metadata(
        tmp_path, init_file="soma-dash-init.el",
        input_fn=lambda _: "1", inits_dir=inits,
    )
    assert name is not None


def test_cross_ref_monorepo_multiple_matches(tmp_path: Path) -> None:
    """Multiple candidates match multiple use-package declarations."""
    for n in ("ivy", "swiper", "counsel"):
        _make_header_el(tmp_path / f"{n}.el")
    inits = tmp_path / "inits"
    inits.mkdir()
    init = inits / "soma-ivy-counsel-and-swiper-init.el"
    init.write_text(
        "(use-package ivy\n(use-package swiper\n(use-package counsel\n",
        encoding="utf-8",
    )
    _, name = locate_package_metadata(
        tmp_path,
        init_file="soma-ivy-counsel-and-swiper-init.el",
        input_fn=lambda _: "1",
        inits_dir=inits,
    )
    assert name in ("ivy", "swiper", "counsel")
