"""
Regression tests: File > Save As, standalone (not via the "Save now?"
Discard/Save prompt -- see test_new_project_unsaved_changes.py for that).

Confirmed test plan (live-verified against the real app, 2026-08-23):

  1. A fresh project's toolbar name is exactly "VEXcode Project".
  2. A fresh project's save status is exactly "Not Saving".
  3. Adding a block leaves the status "Not Saving" (still unsaved) -- it
     does not change on edit alone, only on an actual save.
  4. File > Save As opens the (mocked) native save picker directly.
  5. Entering a name and saving updates the toolbar name to that name.
  6. The status flips "Not Saving" -> "Saving..." -> "Saved". The
     "Saving..." state is real but resolves in ~10ms against the mock by
     default -- too fast to reliably observe -- so the transition test
     below uses save_mock.set_save_delay() to widen that window.
  7. Save As can be run again on an already-saved project: it reopens the
     picker (no "Save now?" interruption) and updates the toolbar name to
     the newly entered name; status remains "Saved" afterward.

Mechanism: same native-dialog problem as every other Save/Open flow in
this suite -- File > Save As calls window.showSaveFilePicker(), mocked via
save_mock (already proven correct by test_save_new_project.py). Filenames
supplied dynamically via the project_name fixture, never hardcoded.
"""
import pytest

from pages import save_mock

pytestmark = pytest.mark.save_as


def test_save_as_updates_name_and_status(file_menu, project_name):
    # 1 -- default toolbar name
    file_menu.expect_project_name("VEXcode Project")

    # 2 -- default save status
    file_menu.expect_saved_status("Not Saving")

    # 3 -- add a block (drag-and-drop substitute, same as
    # test_save_new_project.py -- see that module's docstring)
    file_menu.add_unsaved_blocks_change()
    file_menu.expect_saved_status("Not Saving")

    # 4/5 -- File > Save As with a supplied filename
    first_name = f"{project_name}_saveas1"
    save_mock.set_filename(file_menu.page, first_name)
    file_menu.save_as_current_project()

    file_menu.expect_no_save_error()
    file_menu.expect_project_name(first_name)

    # 6 -- status settles on Saved
    file_menu.expect_saved_status("Saved")

    # 7 -- Save As again with a different name updates the name again
    second_name = f"{project_name}_saveas2"
    save_mock.set_filename(file_menu.page, second_name)
    file_menu.save_as_current_project()

    file_menu.expect_no_save_error()
    file_menu.expect_project_name(second_name)
    file_menu.expect_saved_status("Saved")

    # Bonus, reusing the already-proven save_mock assertions: confirm both
    # saves actually wrote non-empty content under the right filenames,
    # not just that the UI optimistically flipped its status text.
    saved = save_mock.get_saved_files(file_menu.page)
    assert len(saved) == 2, f"Expected exactly two saves, got {saved}"
    assert saved[0]["name"] == first_name
    assert saved[1]["name"] == second_name
    assert saved[0]["content"], "Expected non-empty content on the first save"
    assert saved[1]["content"], "Expected non-empty content on the second save"


def test_save_as_shows_saving_status_transition(file_menu, project_name):
    """Proves "Saving..." is a real, distinct state -- not just a UI
    optimism that jumps straight to "Saved". Uses save_mock.set_save_delay()
    to widen the otherwise ~10ms window (see module docstring, point 6)
    so the transition is actually catchable, both by this assertion and by
    a human watching a headed/--slowmo run."""
    save_mock.set_save_delay(file_menu.page, 800)

    file_menu.add_unsaved_blocks_change()
    save_mock.set_filename(file_menu.page, f"{project_name}_transition")

    transitions = file_menu.capture_save_status_transitions(
        file_menu.save_as_current_project
    )
    texts = [text for _, text in transitions]

    assert "Saving..." in texts, (
        f"Never observed the 'Saving...' status during Save As -- got {transitions}"
    )
    assert texts[-1] == "Saved", f"Expected the final status to be 'Saved' -- got {transitions}"
