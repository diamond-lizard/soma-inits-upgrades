"""Tests for processing.py: tier finders, loop exceptions, handler validation."""

from __future__ import annotations

import pytest

from soma_inits_upgrades.processing import find_next_tier1_task, find_next_tier2_task
from soma_inits_upgrades.state_schema import TIER_1_TASKS, TIER_2_TASKS


def _tier1(done_keys: list[str]) -> dict[str, bool]:
    """Build a tier1_tasks_completed dict with specified keys marked True."""
    return {k: k in done_keys for k in TIER_1_TASKS}


def _tier2(done_keys: list[str]) -> dict[str, bool]:
    """Build a tasks_completed dict with specified keys marked True."""
    return {k: k in done_keys for k in TIER_2_TASKS}


def test_find_next_tier1_some_done() -> None:
    """First incomplete Tier 1 task is returned when some are done."""
    tasks = _tier1(["clone", "default_branch"])
    assert find_next_tier1_task(tasks) == "latest_ref"


def test_find_next_tier1_all_done() -> None:
    """Returns None when all Tier 1 tasks are complete."""
    tasks = _tier1(list(TIER_1_TASKS))
    assert find_next_tier1_task(tasks) is None


def test_find_next_tier1_none_done() -> None:
    """Returns the first Tier 1 task when none are done."""
    tasks = _tier1([])
    assert find_next_tier1_task(tasks) == "clone"


def test_find_next_tier2_some_done() -> None:
    """First incomplete Tier 2 task is returned when some are done."""
    tasks = _tier2(["security_review"])
    assert find_next_tier2_task(tasks) == "upgrade_analysis"


def test_find_next_tier2_all_done() -> None:
    """Returns None when all Tier 2 tasks are complete."""
    tasks = _tier2(list(TIER_2_TASKS))
    assert find_next_tier2_task(tasks) is None


def test_validate_handlers_missing_key() -> None:
    """ValueError raised when TIER_1_HANDLERS misses a task key."""
    from soma_inits_upgrades.processing import TIER_1_HANDLERS, _validate_handlers

    orig = TIER_1_HANDLERS.pop("clone")
    try:
        with pytest.raises(ValueError, match=r"Missing.*clone"):
            _validate_handlers()
    finally:
        TIER_1_HANDLERS["clone"] = orig


def test_validate_handlers_extra_key() -> None:
    """ValueError raised when TIER_2_HANDLERS has extra key."""
    from soma_inits_upgrades.processing import TIER_2_HANDLERS, _validate_handlers

    TIER_2_HANDLERS["bogus"] = lambda ctx: False  # type: ignore[assignment]
    try:
        with pytest.raises(ValueError, match=r"Extra.*bogus"):
            _validate_handlers()
    finally:
        del TIER_2_HANDLERS["bogus"]
