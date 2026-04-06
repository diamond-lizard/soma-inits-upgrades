"""Tests for symbol_collection.py (diff parsing and changed symbol orchestration)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.symbol_collection import extract_changed_symbols

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE_DIFF = """\
--- a/lisp/my-pkg.el
+++ b/lisp/my-pkg.el
@@ -10,5 +10,3 @@
 (require 'cl-lib)
-(defun my-pkg-old-func (arg)
-  "Docstring for old func."
-  (message arg))
-(defvar my-pkg-old-var nil)
+(defun my-pkg-new-func (arg)
+  (message arg))
@@ -30,2 +28,2 @@
-(defcustom my-pkg-removed-opt nil
-  "A removed option.")
+(defcustom my-pkg-new-opt nil
+  "A new option.")
"""



def test_extract_changed_symbols(tmp_path: Path) -> None:
    """Extracts all changed symbols from a diff."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text(SAMPLE_DIFF, encoding="utf-8")
    symbols = extract_changed_symbols(diff_file)
    assert "my-pkg-old-func" in symbols
    assert "my-pkg-old-var" in symbols
    assert "my-pkg-removed-opt" in symbols
    assert "my-pkg-new-func" not in symbols


def test_extract_changed_symbols_mode(tmp_path: Path) -> None:
    """Extracts derived symbols for mode definitions."""
    diff = """\
--- a/my-mode.el
+++ b/my-mode.el
@@ -1,2 +1,1 @@
-(define-minor-mode old-mode
-  "An old mode.")
+(define-minor-mode new-mode
"""
    diff_file = tmp_path / "mode.diff"
    diff_file.write_text(diff, encoding="utf-8")
    symbols = extract_changed_symbols(diff_file)
    assert "old-mode" in symbols
    assert "old-mode-hook" in symbols
    assert "old-mode-map" in symbols
    assert "new-mode" not in symbols


def test_extract_changed_symbols_deduplication(tmp_path: Path) -> None:
    """Deduplicates symbols appearing in multiple hunks."""
    diff = """\
--- a/pkg.el
+++ b/pkg.el
@@ -1,1 +1,1 @@
-(defun my-dup ()
+(defun replacement-1 ()
@@ -10,1 +10,1 @@
-(defun my-dup ()
+(defun replacement-2 ()
"""
    diff_file = tmp_path / "dup.diff"
    diff_file.write_text(diff, encoding="utf-8")
    symbols = extract_changed_symbols(diff_file)
    assert symbols.count("my-dup") == 1


def test_extract_changed_symbols_cosmetic_excluded(tmp_path: Path) -> None:
    """Symbols present on both removed and added lines are excluded."""
    diff = """\
--- a/pkg.el
+++ b/pkg.el
@@ -1,2 +1,2 @@
-(defvar my-var nil "Old docstring.")
+(defvar my-var nil "New docstring.")
-(defun old-func () nil)
+(defun new-func () nil)
"""
    diff_file = tmp_path / "cosmetic.diff"
    diff_file.write_text(diff, encoding="utf-8")
    symbols = extract_changed_symbols(diff_file)
    assert "my-var" not in symbols
    assert "old-func" in symbols
    assert "new-func" not in symbols


def test_extract_changed_symbols_truly_removed_detected(
    tmp_path: Path,
) -> None:
    """Symbols only on removed lines are still detected."""
    diff = """\
--- a/pkg.el
+++ b/pkg.el
@@ -1,1 +1,1 @@
-(defun old-func () nil)
+(defun new-func () nil)
"""
    diff_file = tmp_path / "removed.diff"
    diff_file.write_text(diff, encoding="utf-8")
    symbols = extract_changed_symbols(diff_file)
    assert "old-func" in symbols
    assert "new-func" not in symbols


def test_extract_changed_symbols_autoload_timestamp_excluded(
    tmp_path: Path,
) -> None:
    """Regenerated autoloads with only timestamp changes are excluded."""
    diff = """\
--- a/loaddefs.el
+++ b/loaddefs.el
@@ -1,2 +1,2 @@
-;;;### (autoloads nil "my-pkg" "my-pkg.el" (19362 49086))
-(defvar my-mode nil "doc")
+;;;### (autoloads nil "my-pkg" "my-pkg.el" (19362 45486))
+(defvar my-mode nil "doc")
"""
    diff_file = tmp_path / "autoload.diff"
    diff_file.write_text(diff, encoding="utf-8")
    symbols = extract_changed_symbols(diff_file)
    assert "my-mode" not in symbols


def test_extract_changed_symbols_mode_cosmetic_excluded(
    tmp_path: Path,
) -> None:
    """Mode symbol on both sides excludes derived -hook and -map variants."""
    diff = """\
--- a/mode.el
+++ b/mode.el
@@ -1,1 +1,1 @@
-(define-minor-mode my-mode "Old doc.")
+(define-minor-mode my-mode "New doc.")
"""
    diff_file = tmp_path / "mode.diff"
    diff_file.write_text(diff, encoding="utf-8")
    symbols = extract_changed_symbols(diff_file)
    assert "my-mode" not in symbols
    assert "my-mode-hook" not in symbols
    assert "my-mode-map" not in symbols
