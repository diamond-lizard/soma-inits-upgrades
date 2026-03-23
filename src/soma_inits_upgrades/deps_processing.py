"""Dependency analysis: sexp parsing, built-in filtering, version comparison."""

from __future__ import annotations

import sys


def parse_requirements_sexp(raw: str) -> list[tuple[str, str]]:
    """Parse a Package-Requires s-expression string into (name, version) pairs.

    The s-expression is a list of (package-name "version") pairs.
    Malformed entries are skipped with a warning to stderr.
    Returns an empty list if parsing fails entirely.
    """
    import sexpdata

    try:
        parsed = sexpdata.loads(raw)
    except (ValueError, SyntaxError):
        print(
            f"Warning: failed to parse requirements: {raw!r}",
            file=sys.stderr,
        )
        return []
    if not isinstance(parsed, list):
        return []
    return _collect_pairs(parsed)


def _collect_pairs(entries: list[object]) -> list[tuple[str, str]]:
    """Extract (name, version) pairs from parsed sexp entries."""
    import sexpdata

    results: list[tuple[str, str]] = []
    for entry in entries:
        if not isinstance(entry, list) or len(entry) < 1:
            continue
        name_val = entry[0]
        if isinstance(name_val, sexpdata.Symbol):
            name = name_val.value()
        elif isinstance(name_val, str):
            name = name_val
        else:
            continue
        version = entry[1] if len(entry) > 1 else ""
        if not isinstance(version, str):
            version = str(version)
        results.append((name, version))
    return results

BUILTIN_PACKAGES: set[str] = {
    "emacs",
    "cl-lib",
    "seq",
    "map",
    "nadvice",
    "org",
    "jsonrpc",
    "eldoc",
    "flymake",
    "project",
    "xref",
    "eglot",
}


def filter_dependencies(
    deps: list[tuple[str, str]],
) -> tuple[list[str], str | None]:
    """Filter built-in packages and extract the minimum Emacs version.

    Returns (filtered_package_names, min_emacs_version).
    filtered_package_names contains only non-built-in dependency names.
    min_emacs_version is the version string from the 'emacs' entry, or None.
    """
    min_emacs: str | None = None
    filtered: list[str] = []
    for name, version in deps:
        if name == "emacs":
            min_emacs = version if version else None
            continue
        if name not in BUILTIN_PACKAGES:
            filtered.append(name)
    return filtered, min_emacs


def determine_package_name(
    metadata_package_name: str | None, init_file: str,
) -> str:
    """Resolve canonical package name via 3-way fallback.

    1. Use metadata_package_name if available.
    2. Derive from init file name by stripping soma- prefix and -init.el suffix.
    3. Last resort: strip just the .el suffix.
    """
    if metadata_package_name is not None:
        return metadata_package_name
    if init_file.startswith("soma-") and init_file.endswith("-init.el"):
        return init_file[len("soma-") : -len("-init.el")]
    if init_file.endswith(".el"):
        return init_file[: -len(".el")]
    return init_file


def requires_newer_emacs(
    min_version: str | None, user_version: str,
) -> bool:
    """Check if a package requires a newer Emacs than the user has.

    Uses packaging.version.Version for proper semver comparison.
    Returns False if min_version is None.
    """
    if min_version is None:
        return False
    from packaging.version import Version

    return Version(min_version) > Version(user_version)
