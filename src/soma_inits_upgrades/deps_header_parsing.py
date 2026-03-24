"""Extraction of Package-Requires: values from elisp file headers."""

from __future__ import annotations

import re

_CONTINUATION_RE = re.compile(r"^;+\s+")


def extract_multiline_requires(lines: list[str], header_line_idx: int) -> str:
    """Extract a Package-Requires: value that may span continuation lines.

    Starts after the colon on the header line, then accumulates subsequent
    lines starting with semicolons followed by whitespace.  Stops when
    parentheses are balanced.
    """
    header = lines[header_line_idx]
    value = header.split("Package-Requires:", 1)[1].strip()
    for line in lines[header_line_idx + 1 :]:
        if _is_balanced(value):
            break
        m = _CONTINUATION_RE.match(line)
        if not m:
            break
        value += " " + line[m.end() :]
    return value.strip()


def _is_balanced(text: str) -> bool:
    """Return True when opening and closing parens are equal and non-zero."""
    opens = text.count("(")
    return opens > 0 and opens == text.count(")")
