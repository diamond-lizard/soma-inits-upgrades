"""Tests for collect_removed_lines (diff parsing into removed line lists)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soma_inits_upgrades.symbol_collection import collect_removed_lines

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


def test_collect_removed_lines(tmp_path: Path) -> None:
    """Collects only removed lines from a diff file."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text(SAMPLE_DIFF, encoding="utf-8")
    removed = collect_removed_lines(diff_file)
    assert "(defun my-pkg-old-func (arg)" in removed
    assert "(defvar my-pkg-old-var nil)" in removed
    assert "(defcustom my-pkg-removed-opt nil" in removed
    assert "(defun my-pkg-new-func (arg)" not in removed


def test_collect_removed_lines_embedded_cr(tmp_path: Path) -> None:
    """Parses a diff with an embedded carriage return byte without error."""
    cr = b"\x0d"
    diff_bytes = (
        b"diff --git a/lisp/le-python.el b/lisp/le-python.el\n"
        b"--- a/lisp/le-python.el\n"
        b"+++ b/lisp/le-python.el\n"
        b"@@ -10,3 +10,3 @@\n"
        b" (require 'cl-lib)\n"
        b"-(defun le-python-old-func ()\n"
        b'-  "Docstring."\n'
        b'+(replace-regexp-in-string "' + cr + b'" "" result)\n'
        b"+(defun le-python-new-func ()\n"
    )
    diff_file = tmp_path / "cr.diff"
    diff_file.write_bytes(diff_bytes)
    removed = collect_removed_lines(diff_file)
    assert "(defun le-python-old-func ()" in removed
