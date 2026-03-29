"""Shared test data constants for end-to-end validation tests."""

from __future__ import annotations

ENTRY_A = {
    "init_file": "soma-alpha-init.el",
    "repo_url": "https://github.com/test-org/alpha-mode",
    "pinned_ref": "aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111",
}
ENTRY_B = {
    "init_file": "soma-beta-init.el",
    "repo_url": "https://github.com/test-org/beta-mode",
    "pinned_ref": "bbbb2222bbbb2222bbbb2222bbbb2222bbbb2222",
}
RESULTS: list[dict[str, str]] = [ENTRY_A, ENTRY_B]
GROUPED_RESULTS: list[dict[str, object]] = [
    {"init_file": ENTRY_A["init_file"], "repos": [
        {"repo_url": ENTRY_A["repo_url"],
         "pinned_ref": ENTRY_A["pinned_ref"]}]},
    {"init_file": ENTRY_B["init_file"], "repos": [
        {"repo_url": ENTRY_B["repo_url"],
         "pinned_ref": ENTRY_B["pinned_ref"]}]},
]

DIFF_WITH_DEFUN = (
    "diff --git a/alpha.el b/alpha.el\n"
    "--- a/alpha.el\n"
    "+++ b/alpha.el\n"
    "@@ -1,2 +1,4 @@\n"
    "-(defun alpha-old-fn ()\n"
    "-  \"Old function.\")\n"
    "+(defun alpha-new-fn ()\n"
    "+  \"New function.\")\n"
    "+(defun alpha-extra-fn (x)\n"
    "+  \"Extra function.\")\n"
)
LATEST_REF = "abc123abc123abc123abc123abc123abc123abc1"

REPORT_TEMPLATE = (
    "# Upgrade Process\n\n"
    "## Summary of Changes\n\nMinor additions.\n\n"
    "## Breaking Changes\n\nNone.\n\n"
    "## New Dependencies\n\nNone.\n\n"
    "## Removed or Changed Public API\n\nNone.\n\n"
    "## Configuration Impact\n\nMinimal.\n\n"
    "## Emacs Version\n\nNo change.\n\n"
    "## Recommended Upgrade Approach\n\nDirect upgrade.\n"
)
