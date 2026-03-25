"""Fake ripgrep and xclip subprocess factories for testing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fakes import make_completed_process

if TYPE_CHECKING:
    import subprocess


def _build_rg_match_record(symbol: str, fpath: str) -> str:
    """Build a single ripgrep JSON match record."""
    import json
    record = {
        "type": "match",
        "data": {
            "path": {"text": fpath},
            "submatches": [{"match": {"text": symbol}}],
        },
    }
    return json.dumps(record)

class FakeRg:
    """Fake ripgrep subprocess runner with configurable matches."""

    def __init__(self, matches: dict[str, list[str]] | None = None) -> None:
        """Initialize with symbol-to-files mapping."""
        self.matches = matches or {}
        self.operations: list[tuple[str, list[str]]] = []

    def __call__(
        self, args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        """Simulate ripgrep JSON output."""
        arg_list = args if isinstance(args, list) else args.split()
        self.operations.append(("rg", arg_list))
        lines = [
            _build_rg_match_record(sym, fp)
            for sym, files in self.matches.items()
            for fp in files
        ]
        rc = 0 if lines else 1
        return make_completed_process(rc, stdout="\n".join(lines))


def make_fake_rg(matches: dict[str, list[str]] | None = None) -> FakeRg:
    """Factory for creating FakeRg instances."""
    return FakeRg(matches)


class FakeXclip:
    """Fake xclip runner that records calls."""

    def __init__(self) -> None:
        """Initialize call recorder."""
        self.calls: list[tuple[list[str], str]] = []

    def __call__(
        self, args: list[str] | str, **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        """Record the call and return success."""
        arg_list = args if isinstance(args, list) else args.split()
        input_text = str(kwargs.get("input", ""))
        self.calls.append((arg_list, input_text))
        return make_completed_process()


def make_fake_xclip() -> FakeXclip:
    """Factory for creating FakeXclip instances."""
    return FakeXclip()
