"""Tests for entry retry logic: retries and exhaustion."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.entry_retry import retry_errored_entries
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, RepoState

if TYPE_CHECKING:
    from pathlib import Path

_URL = "https://forge.test/r"


def _entry(ref: str) -> dict[str, object]:
    return {"init_file": "x.el", "repos": [{"repo_url": _URL, "pinned_ref": ref}]}


def test_retry_errored_with_retries(tmp_path: Path) -> None:
    """Errored entries with retries are reset to in_progress."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
    )
    es.status = "error"
    es.retries_remaining = 3
    es.notes = "some error"
    es.tasks_completed["clone"] = True
    atomic_write_json(sd / "x.el.json", es)
    results = [_entry("a")]
    count = retry_errored_entries(results, sd)
    assert count == 1
    from soma_inits_upgrades.state import read_entry_state
    state = read_entry_state(sd / "x.el.json")
    assert state is not None
    assert state.status == "in_progress"
    assert state.retries_remaining == 2
    assert state.tasks_completed["clone"] is True


def test_retry_exhausted(tmp_path: Path) -> None:
    """Errored entries with no retries are skipped."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    es = EntryState(
        init_file="x.el",
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
    )
    es.status = "error"
    es.retries_remaining = 0
    atomic_write_json(sd / "x.el.json", es)
    results = [_entry("a")]
    count = retry_errored_entries(results, sd, input_fn=lambda _: "1")
    assert count == 0
