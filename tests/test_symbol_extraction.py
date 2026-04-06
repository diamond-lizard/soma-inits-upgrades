"""Tests for symbol_extraction.py."""

from __future__ import annotations

from soma_inits_upgrades.symbol_extraction import (
    DEFINITION_FORMS,
    MODE_DEFINITION_FORMS,
    derive_mode_symbols,
    extract_symbol_and_form,
    is_definition_line,
)


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


def test_is_definition_line_defvar_no_value() -> None:
    """Recognizes (defvar sym) with no value as a definition line."""
    assert is_definition_line("(defvar found)")


def test_extract_symbol_and_form_defvar_no_value() -> None:
    """Extracts symbol from (defvar sym) with no value."""
    result = extract_symbol_and_form("(defvar found)")
    assert result == ("found", "defvar")


def test_extract_symbol_and_form_defun_no_space_before_arglist() -> None:
    """Extracts symbol when arglist abuts the function name."""
    result = extract_symbol_and_form(
        "(defun mumamo-chunk-aspnet(pos min max)",
    )
    assert result == ("mumamo-chunk-aspnet", "defun")


def test_extract_symbol_and_form_defun_empty_arglist_no_space() -> None:
    """Extracts symbol when empty arglist abuts the function name."""
    result = extract_symbol_and_form("(defun emacs-buffer-file()")
    assert result == ("emacs-buffer-file", "defun")


def test_extract_symbol_and_form_quoted_list_rejected() -> None:
    """Does not extract a symbol from a definition keyword inside a quoted list."""
    result = extract_symbol_and_form(
        "                 (safe-forms '( defun defmacro",
    )
    assert result is None


def test_extract_symbol_and_form_definition_form_as_symbol() -> None:
    """Rejects extraction when the 'symbol' is itself a definition keyword."""
    result = extract_symbol_and_form("(defun defvar")
    assert result is None


def test_is_definition_line_after_nonwhitespace_rejected() -> None:
    """Does not recognize a definition keyword preceded by non-whitespace content."""
    assert not is_definition_line(
        "                 (safe-forms '( defun defmacro",
    )
