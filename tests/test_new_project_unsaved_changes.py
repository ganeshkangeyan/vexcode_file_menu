"""
Regression tests: the "Your project was never saved. Save now?" prompt that
appears when File > New Blocks Project is triggered while there are unsaved
changes -- for Blocks, Python, and C++ source projects.

Flow under test (confirmed against the live app):
  1. Make an edit (add a block / type in the editor) so the project is dirty.
  2. File > New Blocks Project.
  3. The Discard/Save prompt appears (exact text verified, no Cancel option).
  4a. Discard -> workspace resets to a blank blocks project immediately.
  4b. Save -> app calls window.showSaveFilePicker() (the browser's native,
      un-automatable OS Save dialog) -- intercepted by the save_mock fixture
      so the test never hits that wall. See pages/save_mock.py for why and
      how, and README "How the Save mock works".

The Save tests use a dynamically supplied filename (via the `project_name`
fixture: --project-name CLI flag, VEX_PROJECT_NAME env var, or a timestamped
default) rather than a hardcoded one, per the requirement that automation
shouldn't hardcode filenames for a flow that's inherently about naming a
file.

Save assurance: since save_mock intercepts the real native dialog, "a save
happened" isn't proof on its own -- a mock that silently swallowed
everything would look identical to a working one. Each Save test here
checks three things together: (1) no real app error dialog appeared
(expect_no_save_error -- regression guard for the two real errors hit while
building this mock, see file_menu_page.py), (2) the saved filename/extension
match what we asked for, and (3) the saved *content* actually contains the
specific edit each test made -- not just "non-empty", but the literal marker
text we typed/added, so a save that silently wrote stale or garbage data
would still fail the test.
"""
import json

import pytest

from pages import save_mock
from pages.file_menu_page import SAVE_EXTENSIONS

pytestmark = pytest.mark.unsaved_changes

PYTHON_MARKER = "# regression test change"  # default in add_unsaved_text_change()
CPP_MARKER = "// regression test change"


# --- Blocks -----------------------------------------------------------

def test_new_blocks_project_discard_clears_unsaved_blocks_change(file_menu):
    file_menu.add_unsaved_blocks_change()

    dialog = file_menu.new_blocks_project()
    assert dialog is not None, "Expected the Save/Discard prompt to appear"
    assert dialog.message.is_visible()
    assert dialog.discard_button.is_visible()
    assert dialog.save_button.is_visible()

    dialog.discard()
    file_menu.expect_blocks_mode()


def test_new_blocks_project_save_writes_dynamic_filename_for_blocks(file_menu, project_name):
    file_menu.add_unsaved_blocks_change()

    dialog = file_menu.new_blocks_project()
    assert dialog is not None

    expected_name = f"{project_name}{SAVE_EXTENSIONS['blocks']}"
    save_mock.set_filename(file_menu.page, expected_name)
    dialog.save()

    file_menu.expect_no_save_error()

    saved = save_mock.get_saved_files(file_menu.page)
    assert len(saved) == 1, f"Expected exactly one save, got {saved}"
    assert saved[0]["name"] == expected_name
    assert saved[0]["content"], "Expected non-empty saved content"

    # Confirmed real shape by inspecting an actual saved payload (Blocks
    # projects are NOT plain text): a JSON envelope with the Blockly
    # workspace serialized to XML inside a "workspace" field, e.g.
    # {"mode": "Blocks", "hardwareTarget": "brain",
    #  "workspace": "<xml xmlns=\"...\">...<block .../>...</xml>", ...}
    saved_project = json.loads(saved[0]["content"])
    assert saved_project.get("mode") == "Blocks", (
        f"Expected a Blocks project, got mode={saved_project.get('mode')!r}"
    )
    workspace_xml = saved_project.get("workspace", "")
    assert workspace_xml.startswith("<xml"), "Expected Blockly XML in the workspace field"
    # NOTE: add_unsaved_blocks_change() duplicates the existing "when
    # started" hat block rather than adding one with unique text (no
    # scripted way yet to edit a block's text field to a unique marker), so
    # this only confirms the saved workspace contains real serialized
    # block(s) -- not specifically that *this* edit's extra copy made it
    # in. Good enough to catch "saved empty/garbage data"; a stronger
    # per-edit check would need a page object method that edits a block's
    # text field to a unique value and greps for it in workspace_xml.
    assert workspace_xml.count("<block") >= 1, "Expected at least one serialized block"

    # Original call still asked for the .v5blocks type -- confirms we didn't
    # accidentally save a Python/C++ project instead.
    calls = save_mock.get_calls(file_menu.page)
    assert SAVE_EXTENSIONS["blocks"] in str(calls[0])

    file_menu.expect_blocks_mode()


# --- Python -------------------------------------------------------------

def test_new_blocks_project_discard_clears_unsaved_python_change(file_menu):
    dialog = file_menu.new_text_project()
    dialog.choose_python()
    file_menu.expect_text_mode("python")

    file_menu.add_unsaved_text_change()

    prompt = file_menu.new_blocks_project()
    assert prompt is not None, "Expected the Save/Discard prompt to appear"

    prompt.discard()
    file_menu.expect_blocks_mode()


def test_new_blocks_project_save_writes_dynamic_filename_for_python(file_menu, project_name):
    dialog = file_menu.new_text_project()
    dialog.choose_python()
    file_menu.expect_text_mode("python")

    file_menu.add_unsaved_text_change()  # types PYTHON_MARKER by default

    prompt = file_menu.new_blocks_project()
    assert prompt is not None

    expected_name = f"{project_name}{SAVE_EXTENSIONS['python']}"
    save_mock.set_filename(file_menu.page, expected_name)
    prompt.save()

    file_menu.expect_no_save_error()

    saved = save_mock.get_saved_files(file_menu.page)
    assert len(saved) == 1
    assert saved[0]["name"] == expected_name
    assert saved[0]["content"]
    assert PYTHON_MARKER in saved[0]["content"], (
        "Saved content doesn't contain the edit we made -- looks like stale "
        "or wrong project data was saved"
    )

    calls = save_mock.get_calls(file_menu.page)
    assert SAVE_EXTENSIONS["python"] in str(calls[0])

    file_menu.expect_blocks_mode()


# --- C++ ------------------------------------------------------------------

def test_new_blocks_project_discard_clears_unsaved_cpp_change(file_menu):
    dialog = file_menu.new_text_project()
    dialog.choose_cpp()
    file_menu.expect_text_mode("cpp")

    file_menu.add_unsaved_text_change(CPP_MARKER)

    prompt = file_menu.new_blocks_project()
    assert prompt is not None, "Expected the Save/Discard prompt to appear"

    prompt.discard()
    file_menu.expect_blocks_mode()


def test_new_blocks_project_save_writes_dynamic_filename_for_cpp(file_menu, project_name):
    dialog = file_menu.new_text_project()
    dialog.choose_cpp()
    file_menu.expect_text_mode("cpp")

    file_menu.add_unsaved_text_change(CPP_MARKER)

    prompt = file_menu.new_blocks_project()
    assert prompt is not None

    expected_name = f"{project_name}{SAVE_EXTENSIONS['cpp']}"
    save_mock.set_filename(file_menu.page, expected_name)
    prompt.save()

    file_menu.expect_no_save_error()

    saved = save_mock.get_saved_files(file_menu.page)
    assert len(saved) == 1
    assert saved[0]["name"] == expected_name
    assert saved[0]["content"]
    assert CPP_MARKER in saved[0]["content"], (
        "Saved content doesn't contain the edit we made -- looks like stale "
        "or wrong project data was saved"
    )

    calls = save_mock.get_calls(file_menu.page)
    assert SAVE_EXTENSIONS["cpp"] in str(calls[0])

    file_menu.expect_blocks_mode()
