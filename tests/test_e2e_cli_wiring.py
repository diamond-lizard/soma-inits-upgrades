"""CLI-level end-to-end test: verify all phases dispatch through cli() (TASK-28350).

Pre-populates completed Setup and Entry Processing state so the
pipeline resumes at Graph Finalization, runs through Summary, and
marks the run complete -- all driven through CliRunner.invoke(cli).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from click.testing import CliRunner
from e2e_cli_wiring_helpers import write_entry_state, write_global_state

from soma_inits_upgrades.main import cli
from soma_inits_upgrades.state import read_global_state

if TYPE_CHECKING:
    from pathlib import Path

_ENTRIES = [
    {
        "init_file": "soma-alpha-init.el",
        "repo_url": "https://github.com/test-org/alpha",
        "pinned_ref": "aaa111aaa111aaa111aaa111aaa111aaa111aaa1",
    },
]


def test_cli_dispatches_all_phases(tmp_path: Path) -> None:
    """Invoke cli() and verify all four phases complete."""
    stale_path = _write_stale_json(tmp_path)
    output_dir = tmp_path / "out"
    _pre_populate_state(output_dir, stale_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [str(stale_path), "--output-dir", str(output_dir)],
    )
    assert result.exit_code == 0, (
        f"exit_code={result.exit_code}\n{result.output}"
    )

    gs = read_global_state(output_dir / ".state" / "global.json")
    assert gs is not None
    assert gs.completed is True
    assert gs.phases.setup == "done"
    assert gs.phases.entry_processing == "done"
    assert gs.phases.graph_finalization == "done"
    assert gs.phases.summary == "done"
    assert (output_dir / "security-review-summary.md").is_file()


def _write_stale_json(tmp_path: Path) -> Path:
    """Write the input JSON file and return its path."""
    path = tmp_path / "stale.json"
    path.write_text(
        json.dumps({"results": _ENTRIES}), encoding="utf-8",
    )
    return path


def _pre_populate_state(output_dir: Path, stale_path: Path) -> None:
    """Create all state and output files so the pipeline resumes cleanly."""
    state_dir = output_dir / ".state"
    state_dir.mkdir(parents=True)
    (output_dir / ".tmp").mkdir(parents=True)

    resolved_stale = str(stale_path.resolve())
    write_global_state(state_dir, resolved_stale)
    write_entry_state(state_dir)
    _write_dep_graph(output_dir)
    _write_security_review(output_dir)


def _write_dep_graph(output_dir: Path) -> None:
    """Write a dependency graph with one entry."""
    graph = {
        "soma-alpha-init.el": {
            "packages": [
                {"package": "alpha", "repo_url": "https://github.com/t/alpha",
                 "min_emacs_version": None, "depends_on": []},
            ],
            "depended_on_by": [],
        },
    }
    (output_dir / "soma-inits-dependency-graphs.json").write_text(
        json.dumps(graph, indent=2), encoding="utf-8",
    )


def _write_security_review(output_dir: Path) -> None:
    """Write a security review with a valid Risk Rating line."""
    (output_dir / "soma-alpha-init.el-security-review.md").write_text(
        "# Security Review: alpha\n\nRisk Rating: low\n\nNo concerns.\n",
        encoding="utf-8",
    )
