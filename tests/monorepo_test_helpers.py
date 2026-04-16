"""Shared helpers for monorepo multi-package tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_fake_git

from soma_inits_upgrades.protocols import EntryContext, RepoContext
from soma_inits_upgrades.state import atomic_write_json
from soma_inits_upgrades.state_schema import (
    EntryState,
    GlobalState,
    RepoState,
)

if TYPE_CHECKING:
    from pathlib import Path


def make_init_file(inits_dir: Path, name: str, packages: list[str]) -> None:
    """Create a fake init file with (use-package ...) declarations."""
    inits_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"(use-package {p}\n  :ensure t)" for p in packages]
    (inits_dir / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_el_with_header(
    clone_dir: Path, stem: str, deps_sexp: str,
) -> None:
    """Create a .el file with a Package-Requires: header."""
    content = f';; Package-Requires: {deps_sexp}\n'
    (clone_dir / f"{stem}.el").write_text(content, encoding="utf-8")


def make_pkg_el(clone_dir: Path, stem: str, deps_sexp: str) -> None:
    """Create a -pkg.el file with a define-package form."""
    content = f'(define-package "{stem}" "1.0" "desc" \'{deps_sexp})'
    (clone_dir / f"{stem}-pkg.el").write_text(content, encoding="utf-8")


def make_monorepo_ctx(
    tmp_path: Path,
    init_file: str,
    packages: list[str],
    **git_kw: object,
) -> RepoContext:
    """Build a RepoContext for monorepo multi-package tests."""
    sd = tmp_path / ".state"
    sd.mkdir(parents=True, exist_ok=True)
    td = tmp_path / ".tmp"
    td.mkdir(exist_ok=True)
    inits_dir = tmp_path / "inits"
    make_init_file(inits_dir, init_file, packages)
    es = EntryState(
        init_file=init_file,
        repos=[RepoState(
            repo_url="https://github.com/test/monorepo",
            pinned_ref="aaa", latest_ref="bbb",
            default_branch="main",
        )],
    )
    es.status = "in_progress"
    esp = sd / f"{init_file}.json"
    atomic_write_json(esp, es)
    gs = GlobalState(
        emacs_version="29.1",
        entries_summary={"total": 1, "in_progress": 1},
    )
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    entry_ctx = EntryContext(
        entry_state=es, entry_state_path=esp,
        global_state=gs, global_state_path=gsp,
        entry_idx=1, total=1, output_dir=tmp_path, tmp_dir=td,
        state_dir=sd, init_stem=init_file.replace(".el", ""),
        results=[{
            "init_file": init_file,
            "repos": [{"repo_url": "https://github.com/test/monorepo",
                        "pinned_ref": "aaa"}],
        }],
        xclip_checker=lambda: False,
        run_fn=make_fake_git(checkout_ok=True, **git_kw),
        inits_dir=inits_dir, input_fn=lambda prompt: "1",
    )
    return RepoContext(
        entry_ctx=entry_ctx, repo_state=es.repos[0],
        temp_dir=td, clone_dir=td / "clone",
    )
