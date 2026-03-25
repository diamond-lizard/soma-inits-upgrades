"""Fake subprocess factories for dependency injection testing."""

from __future__ import annotations

import subprocess


def make_completed_process(
    returncode: int = 0, stdout: str = "", stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    """Create a subprocess.CompletedProcess with configurable fields."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr,
    )


class FakeGit:
    """Fake git subprocess runner with configurable behavior and call recording."""

    def __init__(
        self, *, clone_ok: bool = True, branch: str | None = "main",
        latest_ref: str | None = "abc123", ref_exists: bool = True,
        diff_output: str = "diff content", checkout_ok: bool = True,
    ) -> None:
        """Initialize with configurable git behavior."""
        self.clone_ok = clone_ok
        self.branch = branch
        self.latest_ref = latest_ref
        self.ref_exists = ref_exists
        self.diff_output = diff_output
        self.checkout_ok = checkout_ok
        self.operations: list[tuple[str, list[str]]] = []

    def __call__(
        self, args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        """Dispatch on git subcommand and return appropriate result."""
        arg_list = args if isinstance(args, list) else args.split()
        subcmd = _find_git_subcmd(arg_list)
        self.operations.append((subcmd, arg_list))
        result = self._dispatch(subcmd)
        if subcmd == "clone" and result.returncode == 0:
            self._create_clone_dir(arg_list)
        return result

    def _dispatch(self, subcmd: str) -> subprocess.CompletedProcess[str]:
        """Route to the appropriate handler based on git subcommand."""
        handlers: dict[str, subprocess.CompletedProcess[str]] = {
            "clone": make_completed_process(0 if self.clone_ok else 128),
            "symbolic-ref": self._symbolic_ref_result(),
            "rev-parse": self._rev_parse_result(),
            "cat-file": make_completed_process(0 if self.ref_exists else 1),
            "diff": make_completed_process(stdout=self.diff_output),
            "checkout": make_completed_process(0 if self.checkout_ok else 1),
        }
        return handlers.get(subcmd, make_completed_process(1, stderr="unknown command"))

    @staticmethod
    def _create_clone_dir(args: list[str]) -> None:
        """Create the clone target directory on successful clone."""
        from pathlib import Path

        target = args[-1] if args else None
        if target and not target.startswith("-"):
            Path(target).mkdir(parents=True, exist_ok=True)

    def _symbolic_ref_result(self) -> subprocess.CompletedProcess[str]:
        """Return result for symbolic-ref command."""
        if self.branch is None:
            return make_completed_process(128, stderr="not a symbolic ref")
        return make_completed_process(stdout=f"refs/remotes/origin/{self.branch}\n")

    def _rev_parse_result(self) -> subprocess.CompletedProcess[str]:
        """Return result for rev-parse command."""
        if self.latest_ref is None:
            return make_completed_process(128, stderr="unknown revision")
        return make_completed_process(stdout=f"{self.latest_ref}\n")


def _find_git_subcmd(args: list[str]) -> str:
    """Extract the git subcommand from an argument list."""
    for arg in args:
        if arg != "git" and not arg.startswith("-"):
            return arg
    return "unknown"


def make_fake_git(**kwargs: object) -> FakeGit:
    """Factory for creating FakeGit instances with configurable behavior."""
    return FakeGit(**kwargs)  # type: ignore[arg-type]

