"""Helpers for test_e2e_cli_wiring: global and entry state writers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from soma_inits_upgrades.state_schema import TIER_2_TASKS

if TYPE_CHECKING:
    from pathlib import Path

_ENTRIES = [
    {
        "init_file": "soma-alpha-init.el",
        "repo_url": "https://github.com/test-org/alpha",
        "pinned_ref": "aaa111aaa111aaa111aaa111aaa111aaa111aaa1",
    },
]


def write_global_state(state_dir: Path, stale_path: str) -> None:
    """Write global state with setup and entry_processing done."""
    gs = {
        "emacs_version": "29.1",
        "stale_inits_file": stale_path,
        "phases": {
            "setup": "done",
            "entry_processing": "done",
            "graph_finalization": "pending",
            "summary": "pending",
        },
        "current_entry": None,
        "entries_summary": {
            "total": 1, "done": 1,
            "in_progress": 0, "pending": 0, "error": 0,
        },
        "graph_finalization_tasks": {
            "inversion": False,
            "validation": False,
            "completion": False,
        },
        "summary_tasks": {
            "security_summary": False,
            "version_conflicts": False,
            "completion": False,
        },
        "entry_names": ["soma-alpha-init.el"],
        "completed": False,
        "date_completed": None,
    }
    (state_dir / "global.json").write_text(
        json.dumps(gs, indent=2), encoding="utf-8",
    )


def write_entry_state(state_dir: Path) -> None:
    """Write per-entry state with all tasks completed."""
    entry = _ENTRIES[0]
    tasks = dict.fromkeys((*TIER_2_TASKS, "temp_cleanup"), True)
    es = {
        "init_file": entry["init_file"],
        "repos": [{
            "repo_url": entry["repo_url"],
            "pinned_ref": entry["pinned_ref"],
            "latest_ref": "fff999fff999fff999fff999fff999fff999fff9",
            "default_branch": "main",
            "package_name": "alpha",
            "min_emacs_version": None,
            "emacs_upgrade_required": False,
            "depends_on": [],
            "done_reason": None,
            "notes": None,
            "tier1_tasks_completed": {
                "clone": True, "default_branch": True,
                "latest_ref": True, "diff": True, "deps": True,
                "version_check": True, "symbols": True,
            },
        }],
        "status": "done",
        "notes": None,
        "done_reason": None,
        "retries_remaining": 5,
        "tasks_completed": tasks,
    }
    (state_dir / "soma-alpha-init.el.json").write_text(
        json.dumps(es, indent=2), encoding="utf-8",
    )
