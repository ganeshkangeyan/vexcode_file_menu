"""
Regression tests: File > New Blocks Project / File > New Text Project.

Scope for this suite (per current test plan): only the "New Project" family
of File menu actions. See README for how to extend to Open/Save/etc.
"""
import pytest

pytestmark = pytest.mark.new_project


def test_new_blocks_project_resets_to_blank_blocks_canvas(file_menu):
    """File > New Blocks Project should land on the default blocks-mode
    canvas with the single 'when started' hat block, DOWNLOAD button visible,
    and no Edit menu (Edit only exists in text/code mode)."""
    file_menu.new_blocks_project()
    file_menu.expect_blocks_mode()


def test_new_text_project_dialog_opens_with_python_and_cpp_options(file_menu):
    """File > New Text Project should present a language-selection dialog
    with exactly Python and C++ choices, plus a way to cancel."""
    dialog = file_menu.new_text_project()

    assert dialog.python_card.is_visible()
    assert dialog.cpp_card.is_visible()
    assert dialog.cancel_button.is_visible()


def test_new_text_project_python_generates_python_boilerplate(file_menu):
    """Choosing Python should switch to the code editor with Python
    boilerplate (from vex import *) and a clean Errors panel (0/0)."""
    dialog = file_menu.new_text_project()
    dialog.choose_python()

    file_menu.expect_text_mode("python")
    file_menu.expect_zero_errors()


def test_new_text_project_cpp_generates_cpp_boilerplate(file_menu):
    """Choosing C++ should switch to the code editor with C++ boilerplate
    (#include "vex.h") and a clean Errors panel (0/0)."""
    dialog = file_menu.new_text_project()
    dialog.choose_cpp()

    file_menu.expect_text_mode("cpp")
    file_menu.expect_zero_errors()


def test_new_text_project_cancel_leaves_current_project_untouched(file_menu):
    """Cancelling the language dialog should close it without altering
    whatever project/mode was active beforehand."""
    file_menu.expect_blocks_mode()  # fresh page load starts in blocks mode

    dialog = file_menu.new_text_project()
    dialog.expect_visible()
    dialog.cancel()

    assert dialog.title.is_hidden()
    file_menu.expect_blocks_mode()  # unchanged


def test_new_blocks_project_switches_back_from_text_mode(file_menu):
    """Regression case for mode-switch bugs: starting a text project then
    using File > New Blocks Project should cleanly return to blocks mode."""
    dialog = file_menu.new_text_project()
    dialog.choose_python()
    file_menu.expect_text_mode("python")

    file_menu.new_blocks_project()
    file_menu.expect_blocks_mode()
