"""Tests for repo_utils.py."""

from __future__ import annotations

import pytest

from soma_inits_upgrades.repo_utils import derive_repo_dir_name


def test_standard_github_url() -> None:
    """Standard HTTPS GitHub URL produces org--repo."""
    url = "https://github.com/emacs-packages/outshine"
    assert derive_repo_dir_name(url) == "emacs-packages--outshine"


def test_trailing_slash() -> None:
    """Trailing slash is stripped before extraction."""
    url = "https://github.com/emacs-packages/outshine/"
    assert derive_repo_dir_name(url) == "emacs-packages--outshine"


def test_dot_git_suffix() -> None:
    """.git suffix is stripped before extraction."""
    url = "https://github.com/emacs-packages/outshine.git"
    assert derive_repo_dir_name(url) == "emacs-packages--outshine"


def test_trailing_slash_and_dot_git() -> None:
    """Both trailing slash and .git are handled."""
    url = "https://github.com/emacs-packages/outshine.git/"
    assert derive_repo_dir_name(url) == "emacs-packages--outshine"


def test_different_org() -> None:
    """Different org name is captured correctly."""
    url = "https://github.com/magnars/dash.el"
    assert derive_repo_dir_name(url) == "magnars--dash.el"


def test_invalid_url_too_short() -> None:
    """URL with fewer than 2 path segments raises ValueError."""
    with pytest.raises(ValueError, match=r"Empty org or repo"):
        derive_repo_dir_name("https://github.com")


def test_invalid_url_empty_parts() -> None:
    """URL with empty org or repo raises ValueError."""
    with pytest.raises(ValueError, match=r"Empty org or repo"):
        derive_repo_dir_name("https://github.com//outshine")


def test_artifact_paths_per_repo_subdirectory() -> None:
    """Verify per-repo artifacts live under the init-file temp directory."""
    from pathlib import Path

    init_stem = "soma-outshine-and-outorg-init"
    tmp_dir = Path("/out/.tmp") / init_stem
    repo_url = "https://github.com/emacs-packages/outshine"
    repo_dir = tmp_dir / derive_repo_dir_name(repo_url)
    assert repo_dir == Path(
        "/out/.tmp/soma-outshine-and-outorg-init"
        "/emacs-packages--outshine",
    )
    diff_path = repo_dir / f"{init_stem}.diff"
    assert diff_path == Path(
        "/out/.tmp/soma-outshine-and-outorg-init"
        "/emacs-packages--outshine"
        "/soma-outshine-and-outorg-init.diff",
    )
