"""Shared setup for multi-repo integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.graph import write_graph
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import EntryState, GlobalState, RepoState

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.validation_schema import GroupedEntryDict

INIT_FILE = "soma-test-init.el"
INIT_STEM = "soma-test-init"
URL_A = "https://github.com/alpha/outshine"
URL_B = "https://github.com/beta/outorg"
DIR_A = "alpha--outshine"
DIR_B = "beta--outorg"
PIN_A = "aaa111"
PIN_B = "bbb222"


def two_repo_entry() -> GroupedEntryDict:
    """Build a grouped entry dict with two repos."""
    return {"init_file": INIT_FILE, "repos": [
        {"repo_url": URL_A, "pinned_ref": PIN_A},
        {"repo_url": URL_B, "pinned_ref": PIN_B},
    ]}


def setup_two_repo(
    tmp_path: Path,
) -> tuple[GroupedEntryDict, GlobalState, Path, Path]:
    """Create dirs, state files, and graph for two-repo tests."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    (tmp_path / ".tmp").mkdir()
    entry = two_repo_entry()
    es = EntryState(
        init_file=INIT_FILE,
        repos=[
            RepoState(repo_url=URL_A, pinned_ref=PIN_A),
            RepoState(repo_url=URL_B, pinned_ref=PIN_B),
        ],
    )
    atomic_write_json(sd / f"{INIT_FILE}.json", es)
    gs = GlobalState(
        entry_names=[INIT_FILE], emacs_version="29.1",
        entries_summary={"total": 1, "pending": 1},
    )
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    write_graph(tmp_path / "soma-inits-dependency-graphs.json", {})
    return entry, gs, sd, gsp


def pre_create_llm_outputs(tmp_path: Path) -> None:
    """Pre-create LLM output files so pauses succeed."""
    (tmp_path / f"{INIT_FILE}-security-review.md").write_text(
        "# Review\nRisk Rating: low\n", encoding="utf-8",
    )
    td = tmp_path / ".tmp" / INIT_STEM
    td.mkdir(parents=True, exist_ok=True)
    (td / f"{INIT_STEM}-upgrade-analysis.json").write_text(
        '{"change_summary": "ok"}', encoding="utf-8",
    )
    (tmp_path / f"{INIT_FILE}-upgrade-process.md").write_text(
        "# Summary of Changes\n## Breaking Changes\n"
        "## New Dependencies\n",
        encoding="utf-8",
    )


def noop_temp_cleanup(ctx: object) -> bool:
    """No-op temp cleanup to preserve artifacts for inspection."""
    from soma_inits_upgrades.protocols import EntryContext

    if isinstance(ctx, EntryContext):
        ctx.entry_state.tasks_completed["temp_cleanup"] = True
    return False
