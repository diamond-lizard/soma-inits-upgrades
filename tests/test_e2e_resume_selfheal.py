"""Integration test: self-healing via resume path when all phases done."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import patch

from e2e_resume_helpers import make_all_done_global, results_for, write_graph
from monorepo_test_helpers import make_init_file
from selfheal_scan_test_helpers import make_done_entry

from soma_inits_upgrades.phase_dispatch_resume import (
    resume_completed_entry_processing,
)
from soma_inits_upgrades.state import read_entry_state

if TYPE_CHECKING:
    from pathlib import Path


def test_bug1_wrong_name_triggers_resume(tmp_path: Path) -> None:
    """Wrong package_name on done entry triggers resume via scan."""
    sd = tmp_path / ".state"
    sd.mkdir()
    od = tmp_path / "output"
    od.mkdir()
    inits = tmp_path / "soma" / "inits"
    entry = "soma-dash-init.el"
    make_init_file(inits, entry, ["dash"])
    make_done_entry(sd, entry, "dash-functional")
    gs = make_all_done_global(sd, [entry])
    write_graph(od, [entry])
    results = results_for([entry])

    with patch("soma_inits_upgrades.symbols.EMACS_DIR", tmp_path):
        got = resume_completed_entry_processing(results, sd, od, gs)

    assert got is True
    es = read_entry_state(sd / f"{entry}.json")
    assert es is not None
    assert es.status == "pending"
    assert es.done_reason is None
    assert gs.phases.entry_processing == "in_progress"
    assert gs.phases.graph_finalization == "pending"
    graph_data = json.loads(
        (od / "soma-inits-dependency-graphs.json").read_text("utf-8"),
    )
    assert entry not in graph_data


def test_bug2_monorepo_mismatch_triggers_resume(tmp_path: Path) -> None:
    """Entry with fewer repos than declarations triggers resume."""
    sd = tmp_path / ".state"
    sd.mkdir()
    od = tmp_path / "output"
    od.mkdir()
    inits = tmp_path / "soma" / "inits"
    entry = "soma-ivy-init.el"
    make_init_file(inits, entry, ["ivy", "swiper", "counsel"])
    make_done_entry(sd, entry, "counsel")
    gs = make_all_done_global(sd, [entry])
    write_graph(od, [entry])
    results = results_for([entry])

    with patch("soma_inits_upgrades.symbols.EMACS_DIR", tmp_path):
        got = resume_completed_entry_processing(results, sd, od, gs)

    assert got is True
    es = read_entry_state(sd / f"{entry}.json")
    assert es is not None
    assert es.status == "pending"
    assert es.done_reason is None
    assert gs.phases.entry_processing == "in_progress"
