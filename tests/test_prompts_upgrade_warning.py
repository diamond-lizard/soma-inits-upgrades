"""Tests for unverified-symbols warning in upgrade prompts."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from soma_inits_upgrades.prompts_upgrade import (
    generate_upgrade_analysis_prompt,
)


def test_upgrade_prompt_includes_unverified_warning(
    tmp_path: Path,
) -> None:
    """Verify warning appears when _unverified_symbols is present."""
    usage = tmp_path / "usage.json"
    usage.write_text(
        json.dumps({"_unverified_symbols": ["evil-mode", "dash-map"]}),
        encoding="utf-8",
    )
    result = generate_upgrade_analysis_prompt(
        [{"package_name": "dash",
          "repo_url": "https://github.com/magnars/dash.el",
          "pinned_ref": "aaa", "latest_ref": "bbb",
          "diff_path": tmp_path / "t.diff",
          "usage_path": usage}],
        tmp_path / "out.json", "",
    )
    assert "WARNING" in result
    assert "evil-mode" in result
    assert "dash-map" in result
    assert "could not be verified" in result


def test_upgrade_prompt_no_warning_without_unverified(
    tmp_path: Path,
) -> None:
    """Verify no warning when _unverified_symbols is absent."""
    usage = tmp_path / "usage.json"
    usage.write_text(
        json.dumps({"some-sym": ["init.el"]}),
        encoding="utf-8",
    )
    result = generate_upgrade_analysis_prompt(
        [{"package_name": "dash",
          "repo_url": "https://github.com/magnars/dash.el",
          "pinned_ref": "aaa", "latest_ref": "bbb",
          "diff_path": tmp_path / "t.diff",
          "usage_path": usage}],
        tmp_path / "out.json", "",
    )
    assert "could not be verified" not in result
