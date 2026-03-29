"""Utility functions for repository URL handling."""

from __future__ import annotations


def derive_repo_dir_name(repo_url: str) -> str:
    """Extract org and repo from a GitHub HTTPS URL as '{org}--{repo}'.

    Handles trailing slashes and .git suffixes.
    Raises ValueError if the URL does not match the expected structure.
    """
    url = repo_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("/")
    if len(parts) < 2:
        msg = f"Cannot derive org/repo from URL: {repo_url}"
        raise ValueError(msg)
    org, repo = parts[-2], parts[-1]
    if not org or not repo:
        msg = f"Empty org or repo in URL: {repo_url}"
        raise ValueError(msg)
    return f"{org}--{repo}"
