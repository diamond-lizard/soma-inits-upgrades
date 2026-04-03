"""Build plain-language warning for unverified symbol searches."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def build_unverified_warning(usage_path: Path) -> str:
    """Build a warning for unverified symbols from usage JSON.

    Reads the JSON at usage_path. If it contains an
    '_unverified_symbols' key, returns a warning paragraph
    instructing the LLM to search for those symbols itself.
    Returns empty string if the file is missing, malformed,
    or has no unverified symbols.
    """
    try:
        raw = usage_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (FileNotFoundError, json.JSONDecodeError):
        return ""
    unverified = data.get("_unverified_symbols")
    if not unverified:
        return ""
    syms = ", ".join(unverified)
    return (
        "\nWARNING: Normally, the usage analysis identifies"
        " which symbols changed upstream AND appear in the"
        " user's Emacs configuration (~/.emacs.d/), so you"
        " can assess whether changes are relevant to the"
        " user. For this package, that automated search"
        " failed. The following changed symbols could not"
        f" be verified: {syms}. Search ~/.emacs.d/ for"
        " references to these symbols yourself, excluding"
        " the elpaca/, straight/, elpa.old/, and"
        " elpaca-upgrade-backup.old/ subdirectories. Treat"
        " any symbols you find as used — analyze their"
        " upstream changes for breakage and include them in"
        " your report. Treat any symbols you do not find"
        " as unused.\n"
    )
