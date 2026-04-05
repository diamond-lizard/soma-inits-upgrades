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


def collect_removed_lines(diff_path: Path) -> list[str]:
    """Parse a diff file and return all removed line contents.

    Uses unidiff to parse the diff into structured objects, then flattens
    files -> hunks -> lines into a flat list of removed line strings.
    """
    import unidiff

    with open(diff_path, encoding="utf-8", newline="\n") as f:
        patch = unidiff.PatchSet(f)
    return [
        line.value.rstrip("\n")
        for pf in patch
        for hunk in pf
        for line in hunk
        if line.is_removed
    ]


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


def extract_changed_symbols(diff_path: Path) -> list[str]:
    """Extract unique changed/removed elisp symbols from a diff file.

    Pipelines removed lines through definition detection, symbol extraction,
    and mode symbol expansion. Returns a deduplicated list.
    """
    all_syms = (
        sym
        for line in collect_removed_lines(diff_path)
        for sym in _symbols_from_line(line)
    )
    seen: set[str] = set()
    result: list[str] = []
    for sym in all_syms:
        if sym not in seen:
            seen.add(sym)
            result.append(sym)
    return result
