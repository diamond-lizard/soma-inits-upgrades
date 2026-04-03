"""Usage analysis JSON I/O: write and read symbol usage data."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def write_usage_analysis(
    data: dict[str, list[str]],
    path: Path,
    *,
    unverified_symbols: list[str] | None = None,
) -> None:
    """Write a usage analysis dictionary to a JSON file.

    When unverified_symbols is provided, an '_unverified_symbols' key
    is added to the output JSON listing symbols whose usage could not
    be verified by the automated search.
    """
    output: dict[str, list[str] | list[str]] = dict(data)
    if unverified_symbols is not None:
        output["_unverified_symbols"] = unverified_symbols
    path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_usage_analysis(path: Path) -> dict[str, list[str]] | None:
    """Read a usage analysis JSON file. Returns None if missing.

    Strips '_unverified_symbols' if present so callers receive a
    clean dict[str, list[str]].
    """
    if not path.exists():
        return None
    data: dict[str, list[str]] = json.loads(path.read_text(encoding="utf-8"))
    data.pop("_unverified_symbols", None)
    return data
