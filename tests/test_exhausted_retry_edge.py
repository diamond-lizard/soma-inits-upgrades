"""Tests for exhausted-retry prompt: edge cases."""

from __future__ import annotations

from typing import TYPE_CHECKING

from exhausted_retry_helpers import entry_dict, errored_state, write_states

from soma_inits_upgrades.entry_retry import retry_errored_entries
from soma_inits_upgrades.state import read_entry_state

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_exhausted_invalid_then_valid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Invalid inputs rejected; valid input eventually accepted."""
    es = errored_state()
    sd = write_states(tmp_path, es)
    inputs = iter(["x", "4", "1"])
    count = retry_errored_entries(
        [entry_dict()], sd,
        input_fn=lambda _: next(inputs),
    )
    assert count == 0
    reloaded = read_entry_state(sd / "x.el.json")
    assert reloaded is not None
    assert reloaded.status == "error"
    err = capsys.readouterr().err
    assert "Please enter a number" in err or "Invalid" in err


def test_exhausted_eoferror_skips(tmp_path: Path) -> None:
    """EOFError at prompt skips entry (like choosing '1')."""
    es = errored_state()
    sd = write_states(tmp_path, es)

    def eof_input(_: str) -> str:
        raise EOFError

    count = retry_errored_entries(
        [entry_dict()], sd, input_fn=eof_input,
    )
    assert count == 0
    reloaded = read_entry_state(sd / "x.el.json")
    assert reloaded is not None
    assert reloaded.status == "error"


def test_exhausted_multiple_entries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Multiple exhausted entries: skip first, retry second."""
    es1 = errored_state("a.el")
    es2 = errored_state("b.el")
    sd = write_states(tmp_path, es1, es2)
    inputs = iter(["1", "2"])
    count = retry_errored_entries(
        [entry_dict("a.el"), entry_dict("b.el")], sd,
        input_fn=lambda _: next(inputs),
    )
    assert count == 1
    a = read_entry_state(sd / "a.el.json")
    assert a is not None
    assert a.status == "error"
    b = read_entry_state(sd / "b.el.json")
    assert b is not None
    assert b.status == "in_progress"
    err = capsys.readouterr().err
    assert "a.el" in err
    assert "b.el" in err


def test_ensure_entry_state_no_double_count(
    tmp_path: Path,
) -> None:
    """Increment skipped when entry already in entry_names."""
    from soma_inits_upgrades.processing_entry import ensure_entry_state
    from soma_inits_upgrades.state_schema import GlobalState
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    gs = GlobalState(
        emacs_version="29.1",
        entries_summary={"total": 1, "pending": 1},
        entry_names=["x.el"],
    )
    entry: dict[str, object] = {
        "init_file": "x.el",
        "repos": [{"repo_url": "https://forge.test/r", "pinned_ref": "a"}],
    }
    result = ensure_entry_state(entry, sd, gs)
    assert result is not None
    assert gs.entries_summary.total == 1
    assert gs.entries_summary.pending == 1
