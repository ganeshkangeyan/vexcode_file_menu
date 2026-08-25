"""
Regression tests: File > Open.

Mechanism (confirmed against the live app, same investigation approach as
Save -- see pages/save_mock.py): File > Open calls
window.showOpenFilePicker(), the browser's native, un-automatable OS file
picker. Intercepted the same way Save is, via open_mock (pages/open_mock.py)
installed in the file_menu fixture (conftest.py).

Fixtures: three real, user-provided VEXcode V5 project files (not
hand-crafted) living in tests/fixtures/, one per project type -- these were
actually exported from the app, so opening them exercises the real JSON
project envelope format (mode/textContent-or-workspace/robotConfig/etc.),
not a guessed shape:
  - Printing Lines and Shapes.v5blocks
  - Changing Velocities.v5python
  - Complex Decisions (AND OR NOT).v5cpp

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
import json
import re
from pathlib import Path

import pytest

from pages import open_mock

pytestmark = pytest.mark.open

FIXTURES_DIR = Path(__file__).parent / "fixtures"

BLOCKS_FIXTURE = FIXTURES_DIR / "Printing Lines and Shapes.v5blocks"
PYTHON_FIXTURE = FIXTURES_DIR / "Changing Velocities.v5python"
CPP_FIXTURE = FIXTURES_DIR / "Complex Decisions (AND OR NOT).v5cpp"

GARBAGE_CONTENT = '{"not": "a real vexcode project"}'


def _block_type_sequence(workspace_xml: str) -> list:
    """Every <block type="..."> / <shadow type="..."> in document order --
    a structural fingerprint of a Blockly workspace's exact content.
    Order-preserving and format-agnostic (doesn't care about attribute
    ordering or whitespace differences between the source file's XML and
    whatever the app re-serializes), unlike a raw string comparison."""
    return re.findall(r'<(?:block|shadow) type="([^"]+)"', workspace_xml)


def _normalize_text(text: str) -> str:
    """Normalize line endings and trailing whitespace before comparing
    clipboard-read editor content against a fixture's raw JSON string --
    avoids false failures from \\r\\n vs \\n or a trailing newline that
    don't reflect an actual content mismatch."""
    return text.replace("\r\n", "\n").strip()


def _open_fixture(file_menu, fixture_path: Path):
    dialog = file_menu.open_project()
    assert dialog is None, (
        "Expected File > Open to proceed directly (no unsaved changes on a "
        "fresh project) but got the Save/Discard prompt instead"
    )


# --- Successful opens, one per project type -------------------------------

def test_open_blocks_project_loads_fixture(file_menu):
    content = BLOCKS_FIXTURE.read_text(encoding="utf-8")
    open_mock.set_file(file_menu.page, BLOCKS_FIXTURE.name, content)

    _open_fixture(file_menu, BLOCKS_FIXTURE)

    file_menu.expect_project_opened(BLOCKS_FIXTURE.stem, "blocks")

    # Exact-content check: read the actual loaded Blockly workspace back
    # via the app's own Blockly API and compare its full block-type
    # sequence against the source fixture's workspace XML -- proves the
    # specific blocks that loaded match the specific file we opened, not
    # just that "some blocks" are present.
    fixture_project = json.loads(content)
    expected_types = _block_type_sequence(fixture_project["workspace"])
    loaded_types = _block_type_sequence(file_menu.get_blocks_workspace_xml())
    assert loaded_types == expected_types, (
        "Loaded workspace's block sequence doesn't match the fixture "
        f"file's -- wrong file may have loaded.\nExpected: {expected_types}\n"
        f"Got: {loaded_types}"
    )
    assert len(loaded_types) > 0, "Sanity check: fixture should contain real blocks"

    calls = open_mock.get_calls(file_menu.page)
    assert len(calls) == 1


def test_open_python_project_loads_fixture(file_menu):
    content = PYTHON_FIXTURE.read_text(encoding="utf-8")
    open_mock.set_file(file_menu.page, PYTHON_FIXTURE.name, content)

    _open_fixture(file_menu, PYTHON_FIXTURE)

    file_menu.expect_project_opened(PYTHON_FIXTURE.stem, "python")

    # Exact-content check: full editor text via clipboard, compared against
    # the fixture's own textContent field -- not a substring/marker.
    fixture_project = json.loads(content)
    expected_text = fixture_project["textContent"]
    loaded_text = file_menu.get_editor_full_text()
    assert _normalize_text(loaded_text) == _normalize_text(expected_text), (
        "Editor content doesn't exactly match the fixture file's source -- "
        "wrong file may have loaded, or content was truncated/corrupted"
    )


def test_open_cpp_project_loads_fixture(file_menu):
    content = CPP_FIXTURE.read_text(encoding="utf-8")
    open_mock.set_file(file_menu.page, CPP_FIXTURE.name, content)

    _open_fixture(file_menu, CPP_FIXTURE)

    file_menu.expect_project_opened(CPP_FIXTURE.stem, "cpp")

    fixture_project = json.loads(content)
    expected_text = fixture_project["textContent"]
    loaded_text = file_menu.get_editor_full_text()
    assert _normalize_text(loaded_text) == _normalize_text(expected_text), (
        "Editor content doesn't exactly match the fixture file's source -- "
        "wrong file may have loaded, or content was truncated/corrupted"
    )


# --- Error / edge cases -----------------------------------------------------

def test_open_unsupported_project_shows_error_and_leaves_project_untouched(file_menu):
    open_mock.set_file(file_menu.page, "garbage.v5blocks", GARBAGE_CONTENT)

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


def test_open_with_unsaved_changes_prompts_then_loads_requested_file(file_menu):
    file_menu.add_unsaved_blocks_change()

    content = PYTHON_FIXTURE.read_text(encoding="utf-8")
    open_mock.set_file(file_menu.page, PYTHON_FIXTURE.name, content)

    dialog = file_menu.open_project()
    assert dialog is not None, (
        "Expected the Save/Discard prompt since the current project has "
        "unsaved changes"
    )

    dialog.discard()

    file_menu.expect_project_opened(PYTHON_FIXTURE.stem, "python")

    fixture_project = json.loads(content)
    expected_text = fixture_project["textContent"]
    loaded_text = file_menu.get_editor_full_text()
    assert _normalize_text(loaded_text) == _normalize_text(expected_text), (
        "Editor content doesn't exactly match the fixture file's source "
        "after the Discard-then-Open flow"
    )
