"""Tests for symbols.py (ripgrep usage search)."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from soma_inits_upgrades.symbols import (
    build_elisp_boundary_pattern,
    parse_rg_json_output,
    read_usage_analysis,
    write_pattern_file,
    write_usage_analysis,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_build_boundary_pattern_simple() -> None:
    """Builds a PCRE2 boundary pattern for a simple symbol."""
    pat = build_elisp_boundary_pattern("evil")
    assert "evil" in pat
    assert "(?<!" in pat
    assert "(?!" in pat


def test_build_boundary_pattern_escapes_regex() -> None:
    """Escapes regex-special characters in symbol names."""
    pat = build_elisp_boundary_pattern("foo.bar")
    assert r"foo\.bar" in pat


def test_build_boundary_pattern_hyphenated() -> None:
    """Handles hyphenated elisp symbols correctly."""
    pat = build_elisp_boundary_pattern("evil-mode")
    assert "evil\\-mode" in pat or "evil-mode" in pat


def test_write_pattern_file(tmp_path: Path) -> None:
    """Writes one pattern per line to a temp file."""
    syms = ["evil", "dash-map"]
    path = write_pattern_file(syms, tmp_path)
    assert path.exists()
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert "evil" in lines[0]
    assert "dash" in lines[1]
    path.unlink()


def _make_rg_match(
    file_path: str, matched_text: str, line_number: int = 1,
) -> str:
    """Build a ripgrep JSON match line."""
    record = {
        "type": "match",
        "data": {
            "path": {"text": file_path},
            "lines": {"text": f"({matched_text})"},
            "line_number": line_number,
            "submatches": [
                {"match": {"text": matched_text}, "start": 1, "end": 5},
            ],
        },
    }
    return json.dumps(record)


def test_parse_rg_json_output_basic() -> None:
    """Parses ripgrep JSON output and maps matches to symbols."""
    symbols = ["evil", "dash"]
    stdout = "\n".join([
        '{"type":"begin","data":{"path":{"text":"init.el"}}}',
        _make_rg_match("init.el", "evil"),
        _make_rg_match("config.el", "dash"),
        _make_rg_match("init.el", "evil"),
        '{"type":"end","data":{"path":{"text":"init.el"}}}',
    ])
    result = parse_rg_json_output(stdout, symbols)
    assert result["evil"] == ["init.el"]
    assert result["dash"] == ["config.el"]


def test_parse_rg_json_output_no_matches() -> None:
    """Returns empty lists when no matches found."""
    result = parse_rg_json_output("", ["evil"])
    assert result == {"evil": []}


def test_parse_rg_json_output_deduplicates_files() -> None:
    """Deduplicates file paths per symbol."""
    stdout = "\n".join([
        _make_rg_match("init.el", "evil", 1),
        _make_rg_match("init.el", "evil", 10),
    ])
    result = parse_rg_json_output(stdout, ["evil"])
    assert result["evil"] == ["init.el"]


def test_write_and_read_usage_analysis(tmp_path: Path) -> None:
    """Round-trips a usage analysis dict through JSON."""
    data = {"evil": ["init.el", "keys.el"], "dash": []}
    path = tmp_path / "usage.json"
    write_usage_analysis(data, path)
    loaded = read_usage_analysis(path)
    assert loaded == data


def test_read_usage_analysis_missing(tmp_path: Path) -> None:
    """Returns None for a nonexistent file."""
    assert read_usage_analysis(tmp_path / "nope.json") is None


def _setup_el_files(root: Path) -> None:
    """Create .el files with known symbol references."""
    (root / "init.el").write_text(
        "(require 'evil)\n(evil-mode 1)\n", encoding="utf-8",
    )
    (root / "config.el").write_text(
        "(setq evil-want-keybinding nil)\n", encoding="utf-8",
    )


def test_search_word_boundary(tmp_path: Path) -> None:
    """Exact symbol matches only, not substrings of longer identifiers."""
    from soma_inits_upgrades.symbols import search_symbol_usages

    root = tmp_path / "emacs"
    root.mkdir()
    (root / "a.el").write_text("(evil)\n", encoding="utf-8")
    (root / "b.el").write_text("(evil-mode 1)\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    tmp_d = tmp_path / "tmp"
    tmp_d.mkdir()
    result = search_symbol_usages(
        ["evil"], root, out, tmp_d,
    )
    paths = result.get("evil", [])
    assert any("a.el" in p for p in paths)
    assert not any("b.el" in p for p in paths)


def test_search_hyphenated_boundary(tmp_path: Path) -> None:
    """Hyphenated symbol matches exactly, not longer variants."""
    from soma_inits_upgrades.symbols import search_symbol_usages

    root = tmp_path / "emacs"
    root.mkdir()
    (root / "a.el").write_text("(foo-bar)\n", encoding="utf-8")
    (root / "b.el").write_text("(foo-bar-baz)\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    tmp_d = tmp_path / "tmp"
    tmp_d.mkdir()
    result = search_symbol_usages(
        ["foo-bar"], root, out, tmp_d,
    )
    paths = result.get("foo-bar", [])
    assert any("a.el" in p for p in paths)
    assert not any("b.el" in p for p in paths)


def test_search_excludes_output_dir(tmp_path: Path) -> None:
    """Dynamically excludes the output directory from search."""
    from soma_inits_upgrades.symbols import search_symbol_usages

    root = tmp_path / "emacs"
    root.mkdir()
    out = root / "output"
    out.mkdir()
    (root / "user.el").write_text("(my-sym)\n", encoding="utf-8")
    (out / "report.el").write_text("(my-sym)\n", encoding="utf-8")
    tmp_d = tmp_path / "tmp"
    tmp_d.mkdir()
    result = search_symbol_usages(
        ["my-sym"], root, out, tmp_d,
    )
    paths = result.get("my-sym", [])
    assert any("user.el" in p for p in paths)
    assert not any("report.el" in p for p in paths)


def test_search_timeout(tmp_path: Path) -> None:
    """Returns empty dict on subprocess timeout."""
    from soma_inits_upgrades.symbols import search_symbol_usages

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
