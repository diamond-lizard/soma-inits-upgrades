"""Diff symbol extraction from removed lines (defun/defvar/etc.), unidiff parsing."""

from __future__ import annotations

import re

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
) + r")\s+([^\s()]+)")


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

