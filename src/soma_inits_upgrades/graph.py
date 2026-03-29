"""Dependency graph: build entries, inversion, validation."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

GraphDict = dict[str, dict[str, Any]]


def read_graph(path: Path) -> tuple[GraphDict, bool]:
    """Read the dependency graph JSON file.

    Returns (graph_dict, restored). If missing, returns ({}, False).
    On invalid JSON, attempts .bak restore. Returns ({}, True) if
    both main and backup are invalid/missing.
    """
    import json

    if not path.exists():
        return {}, False
    try:
        raw = path.read_text(encoding="utf-8")
        return json.loads(raw), False
    except (json.JSONDecodeError, OSError):
        return _restore_from_backup(path)


def _restore_from_backup(path: Path) -> tuple[GraphDict, bool]:
    """Attempt to restore graph from .bak file."""
    import json
    import shutil

    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        print(f"Warning: corrupt graph at {path}, no backup", file=sys.stderr)
        return {}, True
    try:
        raw = bak.read_text(encoding="utf-8")
        graph = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        print(f"Warning: corrupt graph and backup at {path}", file=sys.stderr)
        return {}, True
    shutil.copy2(bak, path)
    print(f"Warning: restored graph from backup at {bak}", file=sys.stderr)
    return graph, True


def write_graph(path: Path, graph: GraphDict) -> None:
    """Write the dependency graph atomically with backup-on-write.

    Creates a .bak copy before writing, then writes via .tmp + rename.
    Raises OSError on write failure.
    """
    import json
    import shutil

    if path.exists():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
    content = json.dumps(graph, indent=2)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)

