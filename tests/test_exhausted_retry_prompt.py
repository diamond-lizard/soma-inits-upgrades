"""Tests for exhausted-retry prompt: basic choices."""

from __future__ import annotations

from typing import TYPE_CHECKING

from exhausted_retry_helpers import entry_dict, errored_state, write_states

from soma_inits_upgrades.entry_retry import retry_errored_entries
from soma_inits_upgrades.state import read_entry_state

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_exhausted_skip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Choosing '1' (skip) leaves entry unchanged."""
    es = errored_state()
    sd = write_states(tmp_path, es)
    inputs = iter(["1"])
    count = retry_errored_entries(
        [entry_dict()], sd,
        input_fn=lambda _: next(inputs),
    )
    assert count == 0
    reloaded = read_entry_state(sd / "x.el.json")
    assert reloaded is not None
    assert reloaded.status == "error"
    assert reloaded.retries_remaining == 0
    err = capsys.readouterr().err
    assert "x.el" in err
    assert "Skip this entry" in err
    assert "Retry once more" in err
    assert "Delete state and start fresh" in err


def test_exhausted_retry(tmp_path: Path) -> None:
    """Choosing '2' (retry) resets entry to in_progress."""
    es = errored_state()
    sd = write_states(tmp_path, es)
    inputs = iter(["2"])
    count = retry_errored_entries(
        [entry_dict()], sd,
        input_fn=lambda _: next(inputs),
    )
    assert count == 1
    reloaded = read_entry_state(sd / "x.el.json")
    assert reloaded is not None
    assert reloaded.status == "in_progress"
    assert reloaded.retries_remaining == 0
    assert reloaded.notes is None
    assert reloaded.done_reason is None
    rr = reloaded.repos[0]
    assert rr.done_reason is None
    assert all(
        v is False for v in rr.tier1_tasks_completed.values()
    )
    assert rr.package_name == "some-pkg"


def test_exhausted_fresh_start(tmp_path: Path) -> None:
    """Choosing '3' (fresh) deletes the state file."""
    es = errored_state()
    sd = write_states(tmp_path, es)
    inputs = iter(["3"])
    count = retry_errored_entries(
        [entry_dict()], sd,
        input_fn=lambda _: next(inputs),
    )
    assert count == 0
    assert not (sd / "x.el.json").exists()
