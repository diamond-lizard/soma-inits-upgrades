"""Tests for output_validation_tasks.py: malformed file cleanup."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.output_validation_tasks import cleanup_malformed_files

if TYPE_CHECKING:
    from pathlib import Path


def test_cleanup_malformed_files(tmp_path: Path) -> None:
    """Malformed files are deleted by cleanup."""
    td = tmp_path / ".tmp" / "x"
    td.mkdir(parents=True)
    (tmp_path / "x.el-security-review.md.malformed").write_text("x")
    (tmp_path / "x.el-upgrade-process.md.malformed").write_text("x")
    (td / "x-upgrade-analysis.json.malformed").write_text("x")
    cleanup_malformed_files(tmp_path, "x.el")
    assert not (tmp_path / "x.el-security-review.md.malformed").exists()
    assert not (tmp_path / "x.el-upgrade-process.md.malformed").exists()
    assert not (td / "x-upgrade-analysis.json.malformed").exists()
