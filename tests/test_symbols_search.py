"""Integration tests for symbols_io.py (search with real rg and DI fakes)."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from soma_inits_upgrades.symbols_io import search_symbol_usages

if TYPE_CHECKING:
    from pathlib import Path


def test_search_word_boundary(tmp_path: Path) -> None:
    """Exact symbol matches only, not substrings of longer identifiers."""
    root = tmp_path / "emacs"
    root.mkdir()
    (root / "a.el").write_text("(evil)\n", encoding="utf-8")
    (root / "b.el").write_text("(evil-mode 1)\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    tmp_d = tmp_path / "tmp"
    tmp_d.mkdir()
    result = search_symbol_usages(["evil"], root, out, tmp_d)
    paths = result.get("evil", [])
    assert any("a.el" in p for p in paths)
    assert not any("b.el" in p for p in paths)


def test_search_hyphenated_boundary(tmp_path: Path) -> None:
    """Hyphenated symbol matches exactly, not longer variants."""
    root = tmp_path / "emacs"
    root.mkdir()
    (root / "a.el").write_text("(foo-bar)\n", encoding="utf-8")
    (root / "b.el").write_text("(foo-bar-baz)\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    tmp_d = tmp_path / "tmp"
    tmp_d.mkdir()
    result = search_symbol_usages(["foo-bar"], root, out, tmp_d)
    paths = result.get("foo-bar", [])
    assert any("a.el" in p for p in paths)
    assert not any("b.el" in p for p in paths)


def test_search_excludes_output_dir(tmp_path: Path) -> None:
    """Dynamically excludes the output directory from search."""
    root = tmp_path / "emacs"
    root.mkdir()
    out = root / "output"
    out.mkdir()
    (root / "user.el").write_text("(my-sym)\n", encoding="utf-8")
    (out / "report.el").write_text("(my-sym)\n", encoding="utf-8")
    tmp_d = tmp_path / "tmp"
    tmp_d.mkdir()
    result = search_symbol_usages(["my-sym"], root, out, tmp_d)
    paths = result.get("my-sym", [])
    assert any("user.el" in p for p in paths)
    assert not any("report.el" in p for p in paths)


def test_search_timeout(tmp_path: Path) -> None:
    """Returns empty dict on subprocess timeout."""
    def timeout_fn(
        args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        """Simulate a timeout."""
        raise subprocess.TimeoutExpired(cmd="rg", timeout=120)

    root = tmp_path / "emacs"
    root.mkdir()
    (root / "a.el").write_text("(evil)\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    tmp_d = tmp_path / "tmp"
    tmp_d.mkdir()
    result = search_symbol_usages(
        ["evil"], root, out, tmp_d, run_fn=timeout_fn,
    )
    assert result == {}


def test_search_empty_symbols(tmp_path: Path) -> None:
    """Returns empty dict for empty symbol list."""
    root = tmp_path / "emacs"
    root.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    tmp_d = tmp_path / "tmp"
    tmp_d.mkdir()
    assert search_symbol_usages([], root, out, tmp_d) == {}
