"""Tests for summary_completion.py: categorize_entries, format_completion_message."""

from __future__ import annotations

from pathlib import Path

from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, RepoState
from soma_inits_upgrades.summary_completion import (
    categorize_entries,
    format_completion_message,
)


def _write_entry(
    state_dir: Path, name: str, status: str = "done",
    done_reason: str | None = None, notes: str | None = None,
) -> None:
    """Write a per-entry state file with given status and reason."""
    es = EntryState(
        init_file=name,
        repos=[RepoState(
            repo_url="https://github.com/test/repo",
            pinned_ref="abc123",
        )],
        status=status,
        done_reason=done_reason, notes=notes,
    )
    atomic_write_json(state_dir / f"{name}.json", es)


def test_categorize_all_types(tmp_path: Path) -> None:
    """Each category is populated correctly."""
    sd = tmp_path
    _write_entry(sd, "a.el", status="done", done_reason=None)
    _write_entry(sd, "b.el", status="error", notes="clone failed")
    _write_entry(sd, "c.el", status="done", done_reason="empty_diff")
    _write_entry(sd, "d.el", status="done", done_reason="skipped")
    _write_entry(sd, "e.el", status="done", done_reason="already_latest")
    names = ["a.el", "b.el", "c.el", "d.el", "e.el"]
    cats = categorize_entries(names, sd)
    assert cats["done"] == ["a.el"]
    assert cats["errored"] == ["b.el: clone failed"]
    assert cats["empty_diff"] == ["c.el"]
    assert cats["skipped"] == ["d.el"]
    assert cats["already_latest"] == ["e.el"]


def test_categorize_missing_state(tmp_path: Path) -> None:
    """Entries with missing state files are skipped."""
    cats = categorize_entries(["missing.el"], tmp_path)
    assert all(len(v) == 0 for v in cats.values())


def test_format_message_all_sections() -> None:
    """Completion message includes all category sections."""
    cats = {
        "done": ["a.el"],
        "errored": ["b.el: clone failed"],
        "empty_diff": ["c.el"],
        "skipped": ["d.el"],
        "already_latest": ["e.el"],
    }
    msg = format_completion_message(cats, 5, Path("/out"))
    assert "5 entries" in msg
    assert "1 completed" in msg
    assert "1 errors" in msg
    assert "clone failed" in msg
    assert "/out" in msg


def test_format_message_seconds_only() -> None:
    """Elapsed under 60s shows seconds only."""
    cats = {"done": [], "errored": [], "empty_diff": [],
            "skipped": [], "already_latest": []}
    msg = format_completion_message(cats, 0, Path("/out"), elapsed_seconds=45)
    assert "45s" in msg
    assert "m" not in msg.split("Completed in")[1]


def test_format_message_minutes_and_seconds() -> None:
    """Elapsed >= 60s shows minutes and seconds."""
    cats = {"done": [], "errored": [], "empty_diff": [],
            "skipped": [], "already_latest": []}
    msg = format_completion_message(cats, 0, Path("/out"), elapsed_seconds=125)
    assert "2m 5s" in msg


def test_format_message_no_timing() -> None:
    """No timing line when elapsed_seconds is None."""
    cats = {"done": [], "errored": [], "empty_diff": [],
            "skipped": [], "already_latest": []}
    msg = format_completion_message(cats, 0, Path("/out"))
    assert "Completed in" not in msg
