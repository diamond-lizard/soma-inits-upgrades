"""Sexpdata parsing helpers for -pkg.el and Package-Requires: headers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def parse_pkg_el(path: Path) -> tuple[str | None, str | None]:
    """Parse a -pkg.el file and return (raw_deps_sexp, package_name).

    The file contains (define-package NAME VERSION [DOCSTRING] REQUIREMENTS).
    DOCSTRING is optional; REQUIREMENTS may be quote-prefixed.
    Returns (None, None) if the file cannot be parsed or has too few arguments.
    """
    import sexpdata

    try:
        text = path.read_text(encoding="utf-8")
        parsed = sexpdata.loads(text)
    except (OSError, UnicodeDecodeError, ValueError, AssertionError):
        return None, None
    if not isinstance(parsed, list) or len(parsed) < 3:
        return None, None
    pkg_name = _extract_string(parsed[1])
    reqs_arg = _select_requirements_arg(parsed)
    if reqs_arg is None:
        return None, pkg_name
    raw = _unwrap_to_string(reqs_arg)
    return raw, pkg_name


def _extract_string(val: object) -> str | None:
    """Extract a plain string from a sexpdata value."""
    import sexpdata

    if isinstance(val, str):
        return val
    if isinstance(val, sexpdata.Symbol):
        return val.value()
    return None


def _select_requirements_arg(parsed: list[object]) -> object | None:
    """Pick the REQUIREMENTS argument from a define-package form.

    parsed[0]=define-package, [1]=NAME, [2]=VERSION, [3]=DOCSTRING or REQS.
    If [3] is a string, it is the DOCSTRING and [4] is REQUIREMENTS.
    If [3] is a list or Quoted, it is REQUIREMENTS directly.
    """
    import sexpdata

    if len(parsed) < 4:
        return None
    fourth = parsed[3]
    if isinstance(fourth, str):
        return parsed[4] if len(parsed) > 4 else None
    if isinstance(fourth, (list, sexpdata.Quoted)):
        return fourth
    return None


def _unwrap_to_string(val: object) -> str:
    """Convert a sexpdata value to its string representation.

    Unwraps Quoted wrappers and converts lists to s-expression strings.
    """
    import sexpdata

    if isinstance(val, sexpdata.Quoted):
        val = val.x
    if isinstance(val, list):
        return sexpdata.dumps(val)
    if isinstance(val, str):
        return val
    return str(val)

