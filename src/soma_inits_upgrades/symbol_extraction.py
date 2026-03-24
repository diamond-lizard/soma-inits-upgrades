"""Diff symbol extraction from removed lines (defun/defvar/etc.), unidiff parsing."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

DEFINITION_FORMS: set[str] = {
    "defun", "defmacro", "defvar", "defcustom", "defconst",
    "defgroup", "defface", "define-minor-mode", "define-derived-mode",
    "define-generic-mode", "define-globalized-minor-mode",
    "cl-defun", "cl-defmacro", "cl-defmethod", "cl-defgeneric",
    "cl-defstruct", "defsubst", "cl-defsubst",
}

MODE_DEFINITION_FORMS: set[str] = {
    "define-minor-mode",
    "define-derived-mode",
    "define-globalized-minor-mode",
}

_COMMENT_RE = re.compile(r"^\s*;")
_DEFFORM_RE = re.compile(r"\(\s*(" + "|".join(
    re.escape(f) for f in sorted(DEFINITION_FORMS, key=len, reverse=True)
) + r")\s+(\S+)")


def is_definition_line(line: str) -> bool:
    """Check if a line contains an elisp definition form.

    Takes a line of content (already without diff '-' prefix) and returns
    True if it is NOT a comment and contains a definition form keyword.
    """
    if _COMMENT_RE.match(line):
        return False
    return _DEFFORM_RE.search(line) is not None


def extract_symbol_and_form(line: str) -> tuple[str, str] | None:
    """Extract the symbol name and definition form from a definition line.

    Returns (symbol_name, form_keyword) or None if no match.
    """
    match = _DEFFORM_RE.search(line)
    if not match:
        return None
    return match.group(2), match.group(1)


def derive_mode_symbols(symbol: str, form: str) -> list[str]:
    """Expand a symbol into its derived symbols for mode definitions.

    Mode definitions (define-minor-mode, etc.) automatically create
    -hook and -map symbols. Returns [symbol] for non-mode forms.
    """
    if form in MODE_DEFINITION_FORMS:
        return [symbol, symbol + "-hook", symbol + "-map"]
    return [symbol]


def collect_removed_lines(diff_path: Path) -> list[str]:
    """Parse a diff file and return all removed line contents.

    Uses unidiff to parse the diff into structured objects, then flattens
    files -> hunks -> lines into a flat list of removed line strings.
    """
    import unidiff

    patch = unidiff.PatchSet.from_filename(str(diff_path), encoding="utf-8")
    return [
        line.value.rstrip("\n")
        for pf in patch
        for hunk in pf
        for line in hunk
        if line.is_removed
    ]


def extract_changed_symbols(diff_path: Path) -> list[str]:
    """Extract unique changed/removed elisp symbols from a diff file.

    Pipelines removed lines through definition detection, symbol extraction,
    and mode symbol expansion. Returns a deduplicated list.
    """
    removed = collect_removed_lines(diff_path)
    seen: set[str] = set()
    result: list[str] = []
    for line in removed:
        if not is_definition_line(line):
            continue
        extracted = extract_symbol_and_form(line)
        if extracted is None:
            continue
        symbol, form = extracted
        for sym in derive_mode_symbols(symbol, form):
            if sym not in seen:
                seen.add(sym)
                result.append(sym)
    return result
