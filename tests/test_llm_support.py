"""Tests for llm_support.py: prompt writing, user action, run_llm_task."""

from __future__ import annotations

from pathlib import Path

from soma_inits_upgrades.llm_support import prompt_user_action, write_prompt_file


def test_write_prompt_file(tmp_path: Path) -> None:
    """Prompt file is created with correct content."""
    p = tmp_path / "prompt.md"
    write_prompt_file("hello world", p)
    assert p.read_text(encoding="utf-8") == "hello world"


def test_prompt_user_action_continue(tmp_path: Path) -> None:
    """Returns continue when file exists and user enters c."""
    out = tmp_path / "output.md"
    out.write_text("content", encoding="utf-8")
    assert prompt_user_action(out, lambda _: "c") == "continue"


def test_prompt_user_action_empty_enter(tmp_path: Path) -> None:
    """Empty enter treated as continue when file exists."""
    out = tmp_path / "output.md"
    out.write_text("content", encoding="utf-8")
    assert prompt_user_action(out, lambda _: "") == "continue"


def test_prompt_user_action_skip() -> None:
    """Returns skip on s input."""
    assert prompt_user_action(Path("/nonexistent"), lambda _: "s") == "skip"


def test_prompt_user_action_quit() -> None:
    """Returns quit on q input."""
    assert prompt_user_action(Path("/nonexistent"), lambda _: "q") == "quit"


def test_prompt_user_action_eof() -> None:
    """Returns quit on EOFError."""
    def eof_fn(_: str) -> str:
        raise EOFError
    assert prompt_user_action(Path("/nonexistent"), eof_fn) == "quit"


def test_prompt_user_action_missing_file_loops(tmp_path: Path) -> None:
    """Loops when file missing, then returns skip."""
    out = tmp_path / "output.md"
    calls = [0]
    def counter_fn(_: str) -> str:
        calls[0] += 1
        return "c" if calls[0] == 1 else "s"
    assert prompt_user_action(out, counter_fn) == "skip"
    assert calls[0] == 2


def test_run_llm_task_skips_when_done(tmp_path: Path) -> None:
    """run_llm_task returns continue when task already complete."""
    from fakes import make_fake_git

    from soma_inits_upgrades.llm_support import run_llm_task
    from soma_inits_upgrades.protocols import EntryContext
    from soma_inits_upgrades.state import atomic_write_json
    from soma_inits_upgrades.state_schema import EntryState, GlobalState

    sd = tmp_path / ".state"
    sd.mkdir(parents=True)
    td = tmp_path / ".tmp"
    td.mkdir()
    es = EntryState(init_file="x.el", repo_url="https://x.com/r", pinned_ref="a")
    es.tasks_completed["security_review"] = True
    esp = sd / "x.el.json"
    atomic_write_json(esp, es)
    gs = GlobalState()
    gsp = sd / "global.json"
    atomic_write_json(gsp, gs)
    ctx = EntryContext(
        entry_state=es, entry_state_path=esp,
        global_state=gs, global_state_path=gsp,
        entry_idx=1, total=1, output_dir=tmp_path, tmp_dir=td,
        state_dir=sd, init_stem="x",
        results=[], xclip_checker=lambda: False,
        run_fn=make_fake_git(),
    )
    result = run_llm_task(
        ctx, "security_review", lambda: "prompt",
        td / "p.md", tmp_path / "out.md",
        [], lambda *a: False, "Test",
    )
    assert result == "continue"
