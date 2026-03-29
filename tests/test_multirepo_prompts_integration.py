"""Integration: two-repo LLM prompt content verification."""

from __future__ import annotations

from typing import TYPE_CHECKING

from multirepo_helpers import (
    DIR_A,
    DIR_B,
    INIT_FILE,
    INIT_STEM,
    PIN_A,
    PIN_B,
    URL_A,
    URL_B,
    setup_two_repo,
)

from soma_inits_upgrades.prompts import generate_security_review_prompt
from soma_inits_upgrades.prompts_upgrade import generate_upgrade_analysis_prompt

if TYPE_CHECKING:
    from pathlib import Path


def _make_repos_info(tmp_path: Path) -> tuple[list, list]:
    """Build security and analysis repo info lists for two repos."""
    tmp_dir = tmp_path / ".tmp" / INIT_STEM
    sec: list[dict] = []
    ana: list[dict] = []
    for url, pin, rdir_name in [(URL_A, PIN_A, DIR_A), (URL_B, PIN_B, DIR_B)]:
        rdir = tmp_dir / rdir_name
        rdir.mkdir(parents=True, exist_ok=True)
        diff = rdir / f"{INIT_STEM}.diff"
        usage = rdir / f"{INIT_STEM}-usage-analysis.json"
        diff.write_text("diff content", encoding="utf-8")
        usage.write_text("{}", encoding="utf-8")
        sec.append({
            "package_name": rdir_name.split("--")[1],
            "repo_url": url, "pinned_ref": pin,
            "latest_ref": "abc123", "diff_path": diff,
        })
        ana.append({
            "package_name": rdir_name.split("--")[1],
            "repo_url": url, "pinned_ref": pin,
            "latest_ref": "abc123",
            "diff_path": diff, "usage_path": usage,
        })
    return sec, ana


def test_security_prompt_lists_both_repos(tmp_path: Path) -> None:
    """Security review prompt includes both repos' diff paths and labels."""
    setup_two_repo(tmp_path)
    sec_info, _ = _make_repos_info(tmp_path)
    output = tmp_path / f"{INIT_FILE}-security-review.md"
    prompt = generate_security_review_prompt(sec_info, output)
    assert URL_A in prompt
    assert URL_B in prompt
    assert PIN_A in prompt
    assert PIN_B in prompt
    assert str(sec_info[0]["diff_path"]) in prompt
    assert str(sec_info[1]["diff_path"]) in prompt


def test_analysis_prompt_lists_both_repos(tmp_path: Path) -> None:
    """Upgrade analysis prompt includes both repos' diff and usage paths."""
    setup_two_repo(tmp_path)
    _, ana_info = _make_repos_info(tmp_path)
    output = tmp_path / f"{INIT_STEM}-upgrade-analysis.json"
    prompt = generate_upgrade_analysis_prompt(ana_info, output, "")
    assert URL_A in prompt
    assert URL_B in prompt
    assert str(ana_info[0]["diff_path"]) in prompt
    assert str(ana_info[1]["diff_path"]) in prompt
    assert str(ana_info[0]["usage_path"]) in prompt
    assert str(ana_info[1]["usage_path"]) in prompt
