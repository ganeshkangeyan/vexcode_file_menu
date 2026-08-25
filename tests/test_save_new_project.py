"""
Regression tests: File > Save on a brand-new, never-saved project.

Confirmed test plan (from the user, testing against the real app -- test
case numbers continue from Open Examples' 19-30):

  31. A fresh project's toolbar name is exactly "VEXcode Project".
  32. A fresh project's save status is exactly "Not Saving".
  33. Adding a block leaves the status "Not Saving" (still unsaved).
  34. File > Save on a never-saved project goes straight to the native
      save picker -- confirmed NO intermediate "Save now?" prompt (that
      prompt only appears when unsaved changes interrupt a DIFFERENT
      action like New Project/Open; a direct Save just saves).
  35. After saving with an entered name, the toolbar name updates from
      "VEXcode Project" to that name.
  36. After saving, the status flips from "Not Saving" to "Saved".

Mechanism: same native-dialog problem as every other Save/Open flow in
this suite -- File > Save calls window.showSaveFilePicker(), which
Playwright cannot drive, so it's mocked via save_mock (already proven
correct by tests/test_new_project_unsaved_changes.py). Filename supplied
dynamically via the project_name fixture, never hardcoded.

Note on step 4 ("Add some Blocks to the workspace using drag and drop"):
this reuses add_unsaved_blocks_change() (right-click duplicate of the
default hat block) rather than a literal drag from the block palette --
both produce an unsaved change on the canvas, which is what steps 32/33
actually need to be true; a literal palette-drag isn't otherwise exercised
by this test.

Locator risk worth flagging: FileMenuPage.save_menu_item ("Save" exact
text) is a known collision candidate -- a different, unrelated "Save"
button elsewhere on the page was already confirmed to collide with an
unscoped locator when the "Save now?" prompt is open (see
UnsavedChangesDialog's save_button docstring in file_menu_page.py).
Deliberately left unscoped rather than guessing a container, so a real
collision surfaces as a clear Playwright strict-mode error instead of
silently clicking the wrong element.
"""
import pytest

from pages import save_mock
from pages.file_menu_page import SAVE_EXTENSIONS

pytestmark = pytest.mark.save


def test_save_new_project_updates_name_and_status(file_menu, project_name):
    # 31 -- default toolbar name
    file_menu.expect_project_name("VEXcode Project")

    # 32 -- default save status
    file_menu.expect_saved_status("Not Saving")

    # step 4 -- add a block (see module docstring on the drag-and-drop
    # substitution)
    file_menu.add_unsaved_blocks_change()

    # 33 -- still unsaved after the edit
    file_menu.expect_saved_status("Not Saving")

    # 34 -- File > Save opens the (mocked) native save picker directly
    expected_name = f"{project_name}{SAVE_EXTENSIONS['blocks']}"
    save_mock.set_filename(file_menu.page, expected_name)
    file_menu.save_current_project()

    file_menu.expect_no_save_error()

    # 35 -- toolbar name updates to the entered name (no extension shown)
    file_menu.expect_project_name(project_name)

    # 36 -- status flips to Saved
    file_menu.expect_saved_status("Saved")

    # Bonus, reusing the already-proven save_mock assertions from
    # test_new_project_unsaved_changes.py: confirm the save actually wrote
    # non-empty content under the right filename, not just that the UI
    # optimistically flipped its status text.
    saved = save_mock.get_saved_files(file_menu.page)
    assert len(saved) == 1, f"Expected exactly one save, got {saved}"
    assert saved[0]["name"] == expected_name
    assert saved[0]["content"], "Expected non-empty saved content"
