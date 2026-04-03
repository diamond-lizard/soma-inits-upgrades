"""Symbol usage search orchestration and rg output parsing."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from soma_inits_upgrades.protocols import SubprocessRunner


from soma_inits_upgrades.subprocess_utils import SubprocessTimeoutError
from soma_inits_upgrades.symbols import (
    RG_SEARCH_TIMEOUT_SECONDS,
    USAGE_SEARCH_EXCLUSION_DIRS,
    run_batched_rg,
    write_pattern_file,
)


def _iter_rg_matches(stdout: str) -> list[tuple[str, str]]:
    """Extract (file_path, matched_text) pairs from rg JSON output."""
    pairs: list[tuple[str, str]] = []
    for raw_line in stdout.splitlines():
        record = json.loads(raw_line)
        if record.get("type") != "match":
            continue
        fp = record["data"]["path"]["text"]
        for sub in record["data"].get("submatches", []):
            pairs.append((fp, sub["match"]["text"]))
    return pairs


def parse_rg_json_output(stdout: str, symbols: list[str]) -> dict[str, list[str]]:
    """Parse ripgrep JSON output, mapping matches back to symbols.

    Returns a dict mapping symbol names to deduplicated file path lists.
    Symbols with no usages map to an empty list.
    """
    result: dict[str, list[str]] = {s: [] for s in symbols}
    seen: dict[str, set[str]] = {s: set() for s in symbols}
    for file_path, matched_text in _iter_rg_matches(stdout):
        if matched_text not in result:
            continue
        if file_path in seen[matched_text]:
            continue
        seen[matched_text].add(file_path)
        result[matched_text].append(file_path)
    return result


def search_symbol_usages(
    symbols: list[str], search_root: Path, output_dir: Path,
    tmp_dir: Path, run_fn: SubprocessRunner | None = None,
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
    except SubprocessTimeoutError:
        msg = f"Warning: symbol search timed out after {RG_SEARCH_TIMEOUT_SECONDS}s"
        print(msg, file=sys.stderr)
        return {}
    finally:
        pattern_file.unlink(missing_ok=True)
    if result.returncode >= 2:
        msg = f"Warning: rg exited with code {result.returncode}: {result.stderr.strip()}"
        print(msg, file=sys.stderr)
        return {}
    if result.returncode == 1:
        return {s: [] for s in symbols}
    return parse_rg_json_output(result.stdout, symbols)

