"""Shared helpers for self-healing package name tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git
from monorepo_test_helpers import make_init_file

from soma_inits_upgrades.protocols import EntryContext
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import (
    EntryState,
    GlobalState,
    RepoState,
)

if TYPE_CHECKING:
    from pathlib import Path


def make_selfheal_ctx(
    tmp_path: Path, init_file: str, packages: list[str],
) -> EntryContext:
    """Build an EntryContext with an init file for self-heal tests."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    inits_dir = tmp_path / "inits"
    make_init_file(inits_dir, init_file, packages)
    es = EntryState(
        init_file=init_file,
        repos=[RepoState(
            repo_url="https://forge.test/r", pinned_ref="a",
        )],
    )
    es.status = "in_progress"
    esp = sd / f"{init_file}.json"
    atomic_write_json(esp, es)
    gs = GlobalState(entries_summary={"total": 1, "in_progress": 1})
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    return EntryContext(
        entry_state=es, entry_state_path=esp,
        global_state=gs, global_state_path=gsp,
        entry_idx=1, total=1, output_dir=tmp_path, tmp_dir=td,
        state_dir=sd, init_stem=init_file.replace(".el", ""),
        results=[], xclip_checker=lambda: False,
        run_fn=make_fake_git(), inits_dir=inits_dir,
    )
