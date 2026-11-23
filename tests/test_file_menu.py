"""
Regression tests: File > New Blocks Project / File > New Text Project.

Scope for this suite (per current test plan): only the "New Project" family
of File menu actions. See README for how to extend to Open/Save/etc.
"""
import pytest

pytestmark = pytest.mark.new_project


def test_new_blocks_project_resets_to_blank_blocks_canvas(file_menu):
    """File > New Blocks Project should land on the default blocks-mode
    canvas: Blockly toolbox showing, the 'when started' hat block, no code
    editor and no Edit menu (Edit only exists in text/code mode)."""
    file_menu.new_blocks_project()
    file_menu.expect_blocks_mode()


@pytest.mark.requires("language_dialog")
def test_new_text_project_dialog_opens_with_language_options(file_menu, site):
    """File > New Text Project should present a language-selection dialog
    with a choice for each text language this product has, plus a way to
    cancel."""
    dialog = file_menu.new_text_project()

    if site.supports("python"):
        assert dialog.python_card.is_visible()
    if site.supports("cpp"):
        assert dialog.cpp_card.is_visible()
    assert dialog.cancel_button.is_visible()


@pytest.mark.requires("python")
def test_new_text_project_python_generates_python_boilerplate(file_menu):
    """Choosing Python should switch to the code editor with this product's
    Python boilerplate (e.g. "from vex import *") and an Errors panel."""
    file_menu.start_text_project("python")
    file_menu.expect_zero_errors()


@pytest.mark.requires("cpp")
def test_new_text_project_cpp_generates_cpp_boilerplate(file_menu):
    """Choosing C++ should switch to the code editor with C++ boilerplate
    (#include "vex.h") and an Errors panel."""
    file_menu.start_text_project("cpp")
    file_menu.expect_zero_errors()


@pytest.mark.requires("language_dialog")
def test_new_text_project_cancel_leaves_current_project_untouched(file_menu):
    """Cancelling the language dialog should close it without altering
    whatever project/mode was active beforehand."""
    file_menu.expect_blocks_mode()  # fresh page load starts in blocks mode

    dialog = file_menu.new_text_project()
    dialog.expect_visible()
    dialog.cancel()

    assert dialog.title.is_hidden()
    file_menu.expect_blocks_mode()  # unchanged


@pytest.mark.requires("text")
def test_new_blocks_project_switches_back_from_text_mode(file_menu, site):
    """Regression case for mode-switch bugs: starting a text project then
    using File > New Blocks Project should cleanly return to blocks mode."""
    file_menu.start_text_project(site.text_languages[0])

    file_menu.new_blocks_project()
    file_menu.expect_blocks_mode()
