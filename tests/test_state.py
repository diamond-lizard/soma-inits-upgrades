"""Tests for state.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.state import (
    atomic_write_json,
    read_entry_state,
    read_global_state,
)
from soma_inits_upgrades.state_schema import GlobalState

if TYPE_CHECKING:
    from pathlib import Path


def test_global_state_defaults() -> None:
    """Verify GlobalState() with no arguments has expected defaults."""
    gs = GlobalState()
    assert gs.phases.setup == "pending"
    assert gs.completed is False
    assert gs.entry_names == []


def test_atomic_write_and_read_global(tmp_path: Path) -> None:
    """Verify atomic write creates file and read returns valid state."""
    path = tmp_path / "global.json"
    gs = GlobalState(emacs_version="29.1")
    atomic_write_json(path, gs)
    assert path.exists()
    assert not path.with_suffix(".json.tmp").exists()
    loaded = read_global_state(path)
    assert loaded is not None
    assert loaded.emacs_version == "29.1"


def test_read_global_state_missing(tmp_path: Path) -> None:
    """Verify read returns None for missing file."""
    assert read_global_state(tmp_path / "nope.json") is None


def test_read_global_state_invalid_json(tmp_path: Path) -> None:
    """Verify read returns None for invalid JSON."""
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    assert read_global_state(path) is None


def test_read_global_state_fills_defaults(tmp_path: Path) -> None:
    """Verify Pydantic fills missing fields with defaults."""
    path = tmp_path / "partial.json"
    path.write_text('{"emacs_version": "28.2"}', encoding="utf-8")
    loaded = read_global_state(path)
    assert loaded is not None
    assert loaded.emacs_version == "28.2"
    assert loaded.phases.setup == "pending"
    assert loaded.completed is False


def test_read_entry_state_invalid(tmp_path: Path) -> None:
    """Verify read returns None for invalid entry state JSON."""
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")
    assert read_entry_state(path) is None
def test_atomic_write_preserves_original_on_failure(tmp_path: Path) -> None:
    """Verify original file unchanged if .tmp write fails."""
    path = tmp_path / "test.json"
    gs = GlobalState(emacs_version="29.1")
    atomic_write_json(path, gs)
    original = path.read_text(encoding="utf-8")
    # Make tmp dir read-only to cause write failure
    import os
    os.chmod(tmp_path, 0o555)
    try:
        atomic_write_json(path, GlobalState(emacs_version="30.0"))
        raise AssertionError("Should have raised")
    except OSError:
        pass
    finally:
        os.chmod(tmp_path, 0o755)
    assert path.read_text(encoding="utf-8") == original
