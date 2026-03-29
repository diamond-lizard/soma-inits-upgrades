"""Input/output validation models: StaleInitsEntry, StaleInitsFile, UpgradeAnalysis."""

from __future__ import annotations

import re
import urllib.parse
from typing import Any, TypedDict

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class FlatEntryDict(TypedDict):
    """Entry dict with flat repo fields (Phases 150-500)."""

    init_file: str
    repo_url: str
    pinned_ref: str


class StaleInitsEntry(BaseModel):
    """A single entry from the stale inits JSON input."""

    init_file: str
    repo_url: str
    pinned_ref: str

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        """Ensure repo_url is a valid HTTPS URL."""
        parsed = urllib.parse.urlparse(v)
        if parsed.scheme != "https":
            raise ValueError(f"repo_url must use https scheme, got {parsed.scheme!r}")
        if not parsed.hostname:
            raise ValueError("repo_url must have a non-empty hostname")
        return v

    @field_validator("pinned_ref")
    @classmethod
    def validate_pinned_ref(cls, v: str) -> str:
        """Reject refs starting with - (argument injection defense)."""
        if not v:
            raise ValueError("pinned_ref must not be empty")
        if v.startswith("-"):
            raise ValueError("pinned_ref must not start with '-'")
        return v


class StaleInitsFile(BaseModel):
    """Top-level structure of the stale inits JSON input."""

    results: list[StaleInitsEntry]

    @model_validator(mode="after")
    def check_duplicate_init_files(self) -> StaleInitsFile:
        """Reject duplicate init_file values."""
        names = [e.init_file for e in self.results]
        dupes = [n for n in names if names.count(n) > 1]
        if dupes:
            raise ValueError(f"duplicate init_file: {dupes[0]!r}")
        return self


class UpgradeAnalysis(BaseModel):
    """Pydantic model for validating LLM-produced upgrade analysis JSON."""

    model_config = ConfigDict(extra="allow")

    breaking_api_changes: list[dict[str, Any]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("breaking_api_changes", "breaking_changes"),
    )
    removed_or_renamed_symbols: list[dict[str, Any]] = Field(
        default_factory=list,
    )
    new_dependencies: list[dict[str, Any]] = Field(default_factory=list)
    changed_dependencies: list[dict[str, Any]] = Field(default_factory=list)
    emacs_version_conflict: bool = False
    change_summary: str = ""


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences wrapping JSON content."""
    stripped = text.strip()
    pattern = r"^```(?:json)?\s*\n(.*)\n```\s*$"
    match = re.match(pattern, stripped, re.DOTALL)
    return match.group(1) if match else text
