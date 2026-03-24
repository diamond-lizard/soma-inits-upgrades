"""Tests for symbol_extraction.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from soma_inits_upgrades.symbol_extraction import (
    DEFINITION_FORMS,
    MODE_DEFINITION_FORMS,
    collect_removed_lines,
    derive_mode_symbols,
    extract_changed_symbols,
    extract_symbol_and_form,
    is_definition_line,
)

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


def test_definition_forms_count() -> None:
    """DEFINITION_FORMS contains all 18 elisp definition form keywords."""
    assert len(DEFINITION_FORMS) == 18


def test_mode_definition_forms_subset() -> None:
    """MODE_DEFINITION_FORMS is a subset of DEFINITION_FORMS."""
    assert MODE_DEFINITION_FORMS <= DEFINITION_FORMS


def test_is_definition_line_defun() -> None:
    """Recognizes a defun line."""
    assert is_definition_line("(defun my-func (arg)")


def test_is_definition_line_defvar() -> None:
    """Recognizes a defvar line."""
    assert is_definition_line("(defvar my-var nil)")


def test_is_definition_line_defsubst() -> None:
    """Recognizes a defsubst line."""
    assert is_definition_line("(defsubst my-inline (x) x)")


def test_is_definition_line_cl_defun() -> None:
    """Recognizes a cl-defun line."""
    assert is_definition_line("(cl-defun my-cl-func (arg &key opt))")


def test_is_definition_line_comment_excluded() -> None:
    """Excludes commented-out definition lines."""
    assert not is_definition_line(";; (defun commented-func (arg))")


def test_is_definition_line_indented_comment() -> None:
    """Excludes indented comments with definitions."""
    assert not is_definition_line("  ;; (defvar commented-var nil)")


def test_is_definition_line_non_definition() -> None:
    """Rejects lines without definition forms."""
    assert not is_definition_line("(message \"hello\")")


def test_is_definition_line_indented_defun() -> None:
    """Recognizes an indented defun."""
    assert is_definition_line("  (defun nested-func ())")


def test_extract_symbol_and_form_defun() -> None:
    """Extracts symbol and form from a defun line."""
    result = extract_symbol_and_form("(defun my-func (arg)")
    assert result == ("my-func", "defun")


def test_extract_symbol_and_form_define_minor_mode() -> None:
    """Extracts symbol and form from a define-minor-mode line."""
    result = extract_symbol_and_form("(define-minor-mode my-mode")
    assert result == ("my-mode", "define-minor-mode")


def test_extract_symbol_and_form_no_match() -> None:
    """Returns None for non-definition lines."""
    assert extract_symbol_and_form("(message \"hi\")") is None


def test_derive_mode_symbols_minor_mode() -> None:
    """Expands define-minor-mode to include -hook and -map."""
    result = derive_mode_symbols("my-mode", "define-minor-mode")
    assert result == ["my-mode", "my-mode-hook", "my-mode-map"]


def test_derive_mode_symbols_derived_mode() -> None:
    """Expands define-derived-mode to include -hook and -map."""
    result = derive_mode_symbols("my-mode", "define-derived-mode")
    assert result == ["my-mode", "my-mode-hook", "my-mode-map"]


def test_derive_mode_symbols_non_mode() -> None:
    """Returns just the symbol for non-mode forms."""
    assert derive_mode_symbols("my-func", "defun") == ["my-func"]


def test_collect_removed_lines(tmp_path: Path) -> None:
    """Collects only removed lines from a diff file."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text(SAMPLE_DIFF, encoding="utf-8")
    removed = collect_removed_lines(diff_file)
    assert "(defun my-pkg-old-func (arg)" in removed
    assert "(defvar my-pkg-old-var nil)" in removed
    assert "(defcustom my-pkg-removed-opt nil" in removed
    assert "(defun my-pkg-new-func (arg)" not in removed


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
