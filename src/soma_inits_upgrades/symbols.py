"""Ripgrep usage search: pattern building, batched search, JSON parsing, usage I/O."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from soma_inits_upgrades.protocols import SubprocessRunner

from soma_inits_upgrades.subprocess_utils import resolve_run

EMACS_DIR: Path = Path.home() / ".emacs.d"

USAGE_SEARCH_EXCLUSION_DIRS: list[Path] = [
    EMACS_DIR / "elpaca",
    EMACS_DIR / "straight",
    EMACS_DIR / "elpa.old",
    EMACS_DIR / "elpaca-upgrade-backup.old",
]

RG_SEARCH_TIMEOUT_SECONDS = 120


def build_elisp_boundary_pattern(symbol: str) -> str:
    """Build a PCRE2 pattern for an elisp symbol with word boundaries.

    Uses negative lookbehind/lookahead with elisp identifier characters
    to prevent false matches on substrings of longer identifiers.
    """
    escaped = re.escape(symbol)
    boundary = r"[a-zA-Z0-9\-_!?/*+=<>]"
    return f"(?<!{boundary}){escaped}(?!{boundary})"


def write_pattern_file(symbols: list[str], tmp_dir: Path) -> Path:
    """Write elisp boundary patterns to a temp file, one per line.

    Returns the path to the written pattern file.
    """
    patterns = [build_elisp_boundary_pattern(s) for s in symbols]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".patterns", delete=False, dir=str(tmp_dir),
    ) as fd:
        fd.write("\n".join(patterns) + "\n")
    return Path(fd.name)


def _build_exclude_globs(
    exclude_dirs: list[Path], search_root: Path,
) -> list[str]:
    """Convert exclusion paths to ripgrep --glob arguments."""
    globs: list[str] = []
    for d in exclude_dirs:
        try:
            rel = d.relative_to(search_root)
        except ValueError:
            continue
        globs.extend(["--glob", f"!**/{rel}/**"])
    return globs


def run_batched_rg(
    pattern_file: Path, search_root: Path,
    exclude_dirs: list[Path],
    run_fn: SubprocessRunner | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke ripgrep with patterns from a file and return the result.

    Uses PCRE2 mode, JSON output, and .el file glob filter.
    """
    run_fn = resolve_run(run_fn)
    cmd = [
        "rg", "-P", "-f", str(pattern_file),
        "--json", "--no-ignore", "--glob", "*.el",
        *_build_exclude_globs(exclude_dirs, search_root),
        str(search_root),
    ]
    return run_fn(
        cmd, capture_output=True, text=True,
        timeout=RG_SEARCH_TIMEOUT_SECONDS,
    )


def parse_rg_json_output(
    stdout: str, symbols: list[str],
) -> dict[str, list[str]]:
    """Parse ripgrep JSON output, mapping matches back to symbols.

    Returns a dict mapping symbol names to deduplicated file path lists.
    Symbols with no usages map to an empty list.
    """
    result: dict[str, list[str]] = {s: [] for s in symbols}
    seen: dict[str, set[str]] = {s: set() for s in symbols}
    for raw_line in stdout.splitlines():
        record = json.loads(raw_line)
        if record.get("type") != "match":
            continue
        data = record["data"]
        file_path = data["path"]["text"]
        for submatch in data.get("submatches", []):
            matched_text = submatch["match"]["text"]
            if matched_text in result and file_path not in seen[matched_text]:
                seen[matched_text].add(file_path)
                result[matched_text].append(file_path)
    return result


def search_symbol_usages(
    symbols: list[str], search_root: Path, output_dir: Path,
    tmp_dir: Path,
    run_fn: SubprocessRunner | None = None,
) -> dict[str, list[str]]:
    """Search for elisp symbol usages in the Emacs config directory.

    Returns a dict mapping symbol names to lists of file paths where
    each symbol is referenced. Returns empty dict on error or timeout.
    """
    if not symbols:
        return {}
    exclude = [*USAGE_SEARCH_EXCLUSION_DIRS, output_dir]
    pattern_file = write_pattern_file(symbols, tmp_dir)
    try:
        result = run_batched_rg(
            pattern_file, search_root, exclude, run_fn,
        )
    except subprocess.TimeoutExpired:
        print(
            f"Warning: symbol search timed out after"
            f" {RG_SEARCH_TIMEOUT_SECONDS} seconds",
            file=sys.stderr,
        )
        return {}
    finally:
        pattern_file.unlink(missing_ok=True)
    if result.returncode >= 2:
        print(
            f"Warning: rg exited with code {result.returncode}:"
            f" {result.stderr.strip()}",
            file=sys.stderr,
        )
        return {}
    if result.returncode == 1:
        return {s: [] for s in symbols}
    return parse_rg_json_output(result.stdout, symbols)


def write_usage_analysis(data: dict[str, list[str]], path: Path) -> None:
    """Write a usage analysis dictionary to a JSON file."""
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_usage_analysis(path: Path) -> dict[str, list[str]] | None:
    """Read a usage analysis JSON file. Returns None if missing."""
    if not path.exists():
        return None
    data: dict[str, list[str]] = json.loads(path.read_text(encoding="utf-8"))
    return data
