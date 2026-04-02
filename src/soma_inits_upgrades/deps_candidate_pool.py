"""Candidate pool construction: merge -pkg.el and header files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.deps_selection import PackageCandidate

if TYPE_CHECKING:
    from pathlib import Path


def build_candidate_pool(
    pkg_el_files: list[Path],
    header_files: list[tuple[Path, int]],
) -> list[PackageCandidate]:
    """Merge -pkg.el and header files into a deduplicated candidate pool.

    Unparseable -pkg.el files are excluded.  When both a -pkg.el and a
    header exist for the same stem, the -pkg.el is preferred.  Results
    are sorted alphabetically by stem.
    """
    candidates = _collect_pkg_el(pkg_el_files) + _collect_headers(header_files)
    deduped = _deduplicate(candidates)
    return sorted(deduped, key=lambda c: c.stem)


def _collect_pkg_el(paths: list[Path]) -> list[PackageCandidate]:
    """Parse -pkg.el files into PackageCandidate objects."""
    from soma_inits_upgrades.deps_parsing import parse_pkg_el

    result: list[PackageCandidate] = []
    for path in paths:
        raw_deps, embedded_name = parse_pkg_el(path)
        if raw_deps is None and embedded_name is None:
            continue
        stem = path.stem.removesuffix("-pkg")
        result.append(PackageCandidate(
            stem=stem, path=path, source_type="pkg_el",
            header_line=None, embedded_name=embedded_name,
            raw_deps=raw_deps,
        ))
    return result


def _collect_headers(
    header_files: list[tuple[Path, int]],
) -> list[PackageCandidate]:
    """Convert header file tuples into PackageCandidate objects."""
    return [
        PackageCandidate(
            stem=path.stem, path=path, source_type="header",
            header_line=line_num, embedded_name=None, raw_deps=None,
        )
        for path, line_num in header_files
    ]


def _deduplicate(
    candidates: list[PackageCandidate],
) -> list[PackageCandidate]:
    """Deduplicate candidates by stem, preferring pkg_el over header."""
    seen: dict[str, PackageCandidate] = {}
    for c in candidates:
        already = seen.get(c.stem)
        if already is None or (c.source_type == "pkg_el" and already.source_type != "pkg_el"):
            seen[c.stem] = c
    return list(seen.values())
