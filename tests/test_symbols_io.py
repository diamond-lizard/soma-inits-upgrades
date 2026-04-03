"""Tests for symbols_io.py (rg output parsing and usage I/O)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from soma_inits_upgrades.symbols_io import (
    parse_rg_json_output,
    read_usage_analysis,
    write_usage_analysis,
)

if TYPE_CHECKING:
    from pathlib import Path


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


def test_write_includes_unverified_symbols(tmp_path: Path) -> None:
    """write_usage_analysis embeds _unverified_symbols in the JSON."""
    path = tmp_path / "usage.json"
    write_usage_analysis({}, path, unverified_symbols=["evil", "dash"])
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["_unverified_symbols"] == ["evil", "dash"]


def test_read_strips_unverified_symbols(tmp_path: Path) -> None:
    """read_usage_analysis strips _unverified_symbols from the dict."""
    path = tmp_path / "usage.json"
    raw = {"_unverified_symbols": ["evil"], "dash": ["init.el"]}
    path.write_text(json.dumps(raw), encoding="utf-8")
    result = read_usage_analysis(path)
    assert result == {"dash": ["init.el"]}
