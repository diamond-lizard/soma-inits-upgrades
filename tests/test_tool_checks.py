"""Tests for tool_checks.py: git/rg availability and version checks."""

from __future__ import annotations

import subprocess

import pytest

from soma_inits_upgrades.tool_checks import (
    check_git_available,
    check_git_version,
    check_rg_available,
    check_rg_pcre2,
)


def test_check_git_available_missing() -> None:
    """Exits with code 1 when git is not found."""
    def no_git(name: str) -> str | None:
        return None

    with pytest.raises(SystemExit, match="1"):
        check_git_available(no_git)


def test_check_git_available_found() -> None:
    """Returns the path when git is found."""
    def has_git(name: str) -> str | None:
        return "/usr/bin/git"

    assert check_git_available(has_git) == "/usr/bin/git"


def test_check_git_version_too_old() -> None:
    """Exits with code 1 when git version is below 2.19."""
    def fake_run(
        args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "git version 2.17.1\n")

    with pytest.raises(SystemExit, match="1"):
        check_git_version("/usr/bin/git", fake_run)


def test_check_git_version_ok() -> None:
    """Does not exit when git version is >= 2.19."""
    def fake_run(
        args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "git version 2.39.2\n")

    check_git_version("/usr/bin/git", fake_run)


def test_check_rg_available_missing() -> None:
    """Exits with code 1 when rg is not found."""
    def no_rg(name: str) -> str | None:
        return None

    with pytest.raises(SystemExit, match="1"):
        check_rg_available(no_rg)


def test_check_rg_available_found() -> None:
    """Returns the path when rg is found."""
    def has_rg(name: str) -> str | None:
        return "/usr/bin/rg"

    assert check_rg_available(has_rg) == "/usr/bin/rg"


def test_check_rg_pcre2_missing() -> None:
    """Exits with code 1 when rg lacks PCRE2 support."""
    def fake_run(
        args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "", "error\n")

    with pytest.raises(SystemExit, match="1"):
        check_rg_pcre2("/usr/bin/rg", fake_run)


def test_check_rg_pcre2_ok() -> None:
    """Does not exit when rg has PCRE2 support."""
    def fake_run(
        args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, "test\n")

    check_rg_pcre2("/usr/bin/rg", fake_run)
