"""Package name resolution and Emacs version comparison."""

from __future__ import annotations


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
