"""Shared fixtures and helpers for end-to-end validation tests.

Provides test data for two fictitious entries pointing to HTTPS repos
with known commit SHAs.  FakeGit returns realistic diff content
containing elisp defun changes.  Clone directories are populated with
-pkg.el files so dependency parsing finds real metadata.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from e2e_data import (
    LATEST_REF,
    REPORT_TEMPLATE,
    RESULTS,
)


def write_stale_json(tmp_path: Path) -> Path:
    """Write the stale inits JSON fixture and return its path."""
    path = tmp_path / "stale.json"
    path.write_text(json.dumps({"results": RESULTS}), encoding="utf-8")
    return path


def pre_create_llm_outputs(output_dir: Path, name: str) -> None:
    """Pre-create all LLM output files for one entry."""
    stem = name.removesuffix(".el")
    _write_security_review(output_dir, name, stem)
    _write_upgrade_analysis(output_dir / ".tmp" / stem, stem)
    _write_upgrade_report(output_dir, name)


def _write_security_review(d: Path, name: str, stem: str) -> None:
    """Write a security review with a valid Risk Rating line."""
    (d / f"{name}-security-review.md").write_text(
        f"# Security Review: {stem}\n\nRisk Rating: low\n\n"
        f"Pinned: aaa Latest: {LATEST_REF}\nNo security concerns.\n",
        encoding="utf-8",
    )


def _write_upgrade_analysis(td: Path, stem: str) -> None:
    """Write valid upgrade analysis JSON matching UpgradeAnalysis schema."""
    td.mkdir(parents=True, exist_ok=True)
    (td / f"{stem}-upgrade-analysis.json").write_text(
        json.dumps({
            "change_summary": "Minor API additions.",
            "breaking_api_changes": [],
            "removed_or_renamed_symbols": [],
            "new_dependencies": [],
            "changed_dependencies": [],
            "emacs_version_conflict": False,
        }),
        encoding="utf-8",
    )


def _write_upgrade_report(output_dir: Path, name: str) -> None:
    """Write an upgrade report with required section headers."""
    (output_dir / f"{name}-upgrade-process.md").write_text(
        REPORT_TEMPLATE, encoding="utf-8",
    )
