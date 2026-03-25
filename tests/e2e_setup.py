"""End-to-end test setup: fake git factory and phase runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from e2e_helpers import DIFF_WITH_DEFUN, LATEST_REF, RESULTS
from fakes import make_fake_git

from soma_inits_upgrades.setup_completion import (
    complete_setup,
    initialize_dep_graph,
    initialize_entry_states,
)
from soma_inits_upgrades.setup_stage import (
    create_tmp_directory,
    initialize_global_state,
    prompt_emacs_version,
)

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.state_schema import GlobalState


def create_pkg_el(clone_dir: Path, pkg_name: str) -> None:
    """Create a minimal -pkg.el file in the clone directory."""
    clone_dir.mkdir(parents=True, exist_ok=True)
    pkg_file = clone_dir / f"{pkg_name}-pkg.el"
    pkg_file.write_text(
        f'(define-package "{pkg_name}" "1.0" "A test package"'
        f" '((emacs \"27.1\")))\n",
        encoding="utf-8",
    )


def run_setup_phase(
    tmp_path: Path, stale_path: Path,
) -> tuple[GlobalState, Path]:
    """Execute the full Setup stage and return (global_state, gs_path)."""
    output_dir = tmp_path / "output"
    state_dir = output_dir / ".state"
    state_dir.mkdir(parents=True)
    gs_path = state_dir / "global.json"
    gs = initialize_global_state(None, gs_path, stale_path)
    prompt_emacs_version(gs, gs_path, prompt_fn=lambda _: "29.1")
    create_tmp_directory(output_dir)
    initialize_entry_states(RESULTS, state_dir, output_dir, gs)
    initialize_dep_graph(output_dir / "soma-inits-dependency-graphs.json")
    complete_setup(gs, gs_path, RESULTS)
    return gs, gs_path


def make_fake_git_for_e2e(tmp_dir: Path) -> object:
    """Create a FakeGit that populates clone dirs with -pkg.el files.

    On a successful clone the wrapper writes a -pkg.el file so the
    dependency parsing task finds real metadata.
    """
    inner = make_fake_git(diff_output=DIFF_WITH_DEFUN, latest_ref=LATEST_REF)
    original_call = inner.__call__

    def wrapper(args: list[str] | str, **kwargs: object) -> object:
        """Delegate to FakeGit and add -pkg.el on clone."""
        result = original_call(args, **kwargs)
        arg_list = args if isinstance(args, list) else args.split()
        if "clone" in arg_list and result.returncode == 0:
            target = arg_list[-1] if arg_list else None
            if target and not target.startswith("-"):
                from pathlib import Path as _Path
                create_pkg_el(_Path(target), _Path(target).name)
        return result

    wrapper.operations = inner.operations  # type: ignore[attr-defined]
    return wrapper
