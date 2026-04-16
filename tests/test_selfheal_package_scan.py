"""Tests for scan_completed_entries_for_selfheal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from monorepo_test_helpers import make_init_file
from selfheal_scan_test_helpers import make_done_entry

from soma_inits_upgrades.selfheal_package_scan import (
    scan_completed_entries_for_selfheal,
)
from soma_inits_upgrades.state import read_entry_state

if TYPE_CHECKING:
    from pathlib import Path


def test_wrong_name_detected_and_reset(tmp_path: Path) -> None:
    """Done entry with wrong package_name is reset to pending."""
    sd = tmp_path / ".state"
    sd.mkdir()
    inits = tmp_path / "inits"
    make_init_file(inits, "soma-dash-init.el", ["dash"])
    make_done_entry(sd, "soma-dash-init.el", "dash-functional")

    result = scan_completed_entries_for_selfheal(
        ["soma-dash-init.el"], sd, inits,
    )

    assert result == ["soma-dash-init.el"]
    reloaded = read_entry_state(sd / "soma-dash-init.el.json")
    assert reloaded is not None
    assert reloaded.status == "pending"
    assert reloaded.done_reason is None
    assert reloaded.notes is None
    assert reloaded.multi_package_verified is False


def test_correct_name_not_reset(tmp_path: Path) -> None:
    """Done entry with correct package_name is left alone."""
    sd = tmp_path / ".state"
    sd.mkdir()
    inits = tmp_path / "inits"
    make_init_file(inits, "soma-dash-init.el", ["dash"])
    make_done_entry(sd, "soma-dash-init.el", "dash")

    result = scan_completed_entries_for_selfheal(
        ["soma-dash-init.el"], sd, inits,
    )

    assert result == []
    reloaded = read_entry_state(sd / "soma-dash-init.el.json")
    assert reloaded is not None
    assert reloaded.status == "done"


def test_monorepo_count_mismatch_detected(tmp_path: Path) -> None:
    """Done entry with fewer repos than declarations is reset."""
    sd = tmp_path / ".state"
    sd.mkdir()
    inits = tmp_path / "inits"
    make_init_file(inits, "soma-ivy-init.el", ["ivy", "swiper", "counsel"])
    make_done_entry(sd, "soma-ivy-init.el", "counsel")

    result = scan_completed_entries_for_selfheal(
        ["soma-ivy-init.el"], sd, inits,
    )

    assert result == ["soma-ivy-init.el"]
    reloaded = read_entry_state(sd / "soma-ivy-init.el.json")
    assert reloaded is not None
    assert reloaded.status == "pending"
    assert reloaded.done_reason is None
    assert reloaded.notes is None
