"""
Regression tests: File > Open.

Mechanism (confirmed against the live app, same investigation approach as
Save -- see pages/save_mock.py): File > Open calls
window.showOpenFilePicker(), the browser's native, un-automatable OS file
picker. Intercepted the same way Save is, via open_mock (pages/open_mock.py)
installed in the file_menu fixture (conftest.py).

Fixtures: one real project file per project type the product supports,
exported from the app itself (not hand-crafted), so opening them exercises
the real JSON project envelope format (mode/textContent-or-workspace/
robotConfig/etc.), not a guessed shape. They live in tests/fixtures/<site>/
and are listed per site in sites.py -- e.g. for V5:
  - Printing Lines and Shapes.v5blocks
  - Changing Velocities.v5python
  - Complex Decisions (AND OR NOT).v5cpp
Each product only accepts its own extensions (.123blocks, .goblocks,
.iqpython, ...) -- a V5 file is "Unsupported project" on IQ.

Test cases, matching the plan confirmed with the user before writing any of
this:
  1. Opening each fixture loads it correctly -- project name, save status,
     mode, AND the exact content (not a substring, the whole file) matches
     what was in the fixture. See "Exact-content verification" below for
     why this needed live investigation before it could be written.
  2. Opening unsupported/garbage content shows the real "Unsupported
     project" error dialog and leaves the current project alone.
  3. Cancelling the native picker (no file configured in open_mock) is a
     no-op -- current project stays exactly as it was.
  4. Opening while there are unsaved changes shows the same "Save now?"
     prompt as New Blocks/Text Project (shared UnsavedChangesDialog); after
     resolving it (Discard here), the Open proceeds and the requested file
     loads -- verified with the same exact-content check as a plain open.

Exact-content verification
---------------------------
A first version of these tests only checked that one marker string (e.g.
one line of a fixture's code) was visible somewhere on the page. That's
weak: it doesn't rule out stale/wrong content that happens to still
contain that one line, and for the Blocks fixture the "unique text" was a
Blockly workspace *comment*, whose on-canvas visibility (collapsed vs.
expanded) was never actually confirmed live -- it could have been silently
asserting nothing useful.

Investigated live against the real app (via Chrome) to find something
stronger:
  - Blocks: `Blockly.getMainWorkspace()` is a real global on this app, and
    `Blockly.Xml.workspaceToDom()` + `domToText()` -- the same
    serialization the app's own Save flow uses -- gives back the exact
    loaded workspace XML. So the loaded block-type sequence can be
    compared directly against the fixture's own workspace XML.
  - Text (Python/C++): confirmed live there's no `window.monaco` (or any
    other global handle) exposed on this app, and Monaco's DOM is
    virtualized (only currently-scrolled-into-view lines exist as text
    nodes), so page-text scraping can only ever see a fragment. The
    reliable path in Playwright is Ctrl+A + Ctrl+C +
    `navigator.clipboard.readText()` (needs the clipboard permissions
    granted in conftest.py) -- gives back the full, exact editor text.

Both are implemented as `FileMenuPage.get_blocks_workspace_xml()` /
`get_editor_full_text()` -- see file_menu_page.py for the full detail.
"""
import pytest

from pages import open_mock

pytestmark = pytest.mark.open

GARBAGE_CONTENT = '{"not": "a real vexcode project"}'


# --- Successful opens, one per project type -------------------------------

@pytest.mark.parametrize("mode", [
    "blocks",
    pytest.param("python", marks=pytest.mark.requires("python")),
    pytest.param("cpp", marks=pytest.mark.requires("cpp")),
])
def test_open_project_loads_fixture(file_menu, site, mode):
    fixture = site.fixture(mode)
    content = fixture.read_text(encoding="utf-8")
    open_mock.set_file(file_menu.page, fixture.name, content)

    dialog = file_menu.open_project()
    assert dialog is None, (
        "Expected File > Open to proceed directly (no unsaved changes on a "
        "fresh project) but got the Save/Discard prompt instead"
    )

    file_menu.expect_project_opened(fixture.stem, mode)

    # Exact-content check: the full Blockly block sequence (blocks) or the
    # full editor text via clipboard (python/cpp) must match the fixture --
    # not just "some blocks"/a marker line.
    file_menu.expect_content_matches_fixture(content, mode)

    calls = open_mock.get_calls(file_menu.page)
    assert len(calls) == 1


# --- Error / edge cases -----------------------------------------------------

def test_open_unsupported_project_shows_error_and_leaves_project_untouched(file_menu, site):
    open_mock.set_file(file_menu.page, f"garbage{site.extensions['blocks']}", GARBAGE_CONTENT)

    dialog = file_menu.open_project()
    assert dialog is None

    file_menu.expect_unsupported_project_error()
    file_menu.dismiss_unsupported_project_error()

    # Current project (a fresh default Blocks project) should be untouched.
    file_menu.expect_blocks_mode()


def test_open_cancel_leaves_project_untouched(file_menu):
    # No file configured in open_mock -- the fake picker rejects with
    # AbortError, exactly like a real user closing the native dialog
    # without picking anything.
    dialog = file_menu.open_project()
    assert dialog is None

    # No error dialog, no change of mode -- still the default fresh project.
    file_menu.expect_no_save_error()
    file_menu.expect_blocks_mode()


def test_open_with_unsaved_changes_prompts_then_loads_requested_file(file_menu, site):
    file_menu.add_unsaved_blocks_change()

    # A text project where the product has one (proves the mode switches
    # too); blocks-only products (123) open their blocks fixture instead.
    mode = site.text_languages[0] if site.text_languages else "blocks"
    fixture = site.fixture(mode)
    content = fixture.read_text(encoding="utf-8")
    open_mock.set_file(file_menu.page, fixture.name, content)

    dialog = file_menu.open_project()
    assert dialog is not None, (
        "Expected the Save/Discard prompt since the current project has "
        "unsaved changes"
    )

    dialog.discard()

    file_menu.expect_project_opened(fixture.stem, mode)
    file_menu.expect_content_matches_fixture(content, mode)
