"""Symbol collection: diff parsing and changed symbol orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.symbol_extraction import (
    derive_mode_symbols,
    extract_symbol_and_form,
    is_definition_line,
)

if TYPE_CHECKING:
    from pathlib import Path


def _collect_lines(diff_path: Path) -> tuple[list[str], list[str]]:
    """Parse a diff and return (removed_lines, added_lines) in one pass."""
    import unidiff

    with open(diff_path, encoding="utf-8", errors="replace", newline="\n") as f:
        patch = unidiff.PatchSet(f)
    removed: list[str] = []
    added: list[str] = []
    for pf in patch:
        for hunk in pf:
            for line in hunk:
                text = line.value.rstrip("\n")
                if line.is_removed:
                    removed.append(text)
                elif line.is_added:
                    added.append(text)
    return removed, added


def collect_removed_lines(diff_path: Path) -> list[str]:
    """Parse a diff file and return all removed line contents.

    Uses unidiff to parse the diff into structured objects, then flattens
    files -> hunks -> lines into a flat list of removed line strings.
    """
    return _collect_lines(diff_path)[0]


def _symbols_from_line(line: str) -> list[str]:
    """Extract expanded symbols from a single definition line.

    Returns an empty list if the line is not a definition.
    """
    if not is_definition_line(line):
        return []
    extracted = extract_symbol_and_form(line)
    if extracted is None:
        return []
    return derive_mode_symbols(extracted[0], extracted[1])


def _extract_syms(lines: list[str]) -> set[str]:
    """Extract all definition symbols from a list of source lines."""
    return {
        sym
        for line in lines
        for sym in _symbols_from_line(line)
    }


def extract_changed_symbols(diff_path: Path) -> list[str]:
    """Extract elisp symbols removed but not re-added in a diff.

    Symbols present on both removed and added lines (cosmetic
    changes like whitespace or timestamp reformatting) are excluded.
    Returns a sorted list for deterministic output.
    """
    removed_lines, added_lines = _collect_lines(diff_path)
    return sorted(_extract_syms(removed_lines) - _extract_syms(added_lines))
