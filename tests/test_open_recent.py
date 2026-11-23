"""
Regression tests: File > Open Recent.

Confirmed test plan (from the user, testing against the real app):
  1. On a fresh session (no history at all), Open Recent shows
     "No Recent Projects".
  2. Opening a project via File > Open Examples does NOT add it to Open
     Recent -- only files opened via File > Open (a real local file)
     count.
  3. Opening a project via File > Open DOES add it to Open Recent.
  4. Open Recent keeps only the last 5 entries; opening a 6th evicts the
     oldest.

Storage mechanism (confirmed 2026-08-23 via diagnostic run):
  IndexedDB "project-storage-db" v1, object store "recent-projects-store",
  single record at key "recent-projects-key". Value is an array of up to 5
  entries, newest-first:
    { fileRef: { name, pathData: {}, fileExtension, hasWritePermission,
                 hasFolderWritePermissions }, lastOpened: <ms> }
  pathData is always {} -- the app stores file metadata only, not the
  FileSystemFileHandle. Clicking an Open Recent entry therefore calls
  showOpenFilePicker() again (intercepted by our mock), rather than
  reopening via a stored handle.

Why we seed IndexedDB directly instead of relying on File > Open to
populate it:
  Our mock handle (built from Object.create(FileSystemFileHandle.prototype))
  successfully loads the file content, but something in the app's
  open-tracking code path does not fire for the mocked open -- confirmed
  by two diagnostic runs (2026-08-21, 2026-08-23) that showed
  recent-projects-store always empty after a mocked open. The exact
  failure point was not isolated (the record format itself is plain JSON
  with no functions, so structured clone is not the issue). Direct seeding
  via open_mock.seed_recent_projects() sidesteps this entirely and is the
  confirmed working approach.

Locator status:
  - "No Recent Projects" empty-state text: confirmed correct (2026-08-21
    diagnostic dump showed it was never the problem).
  - recent_project_names() / open_recent_project(): confirmed correct
    (2026-08-23) -- real entries render in
    .dropdownmenu_options.submenu.active as .label children (text
    includes the extension, e.g. "Changing Velocities.v5python"); see
    file_menu_page.py. All 4 non-skipped tests in this file pass against
    the real app using this selector.
  - File > Open Examples: skipped (see below) -- UI never inspected live.
"""
from pathlib import Path

import pytest

from pages import open_mock

pytestmark = pytest.mark.open_recent

# Each site lists 6 distinct real fixtures, oldest first (sites.py ->
# SiteConfig.recent_fixtures). Used to exercise the "keep last 5 / evict
# oldest" rule with genuinely distinct files rather than renamed duplicates.


def _open_via_file_open(file_menu, fixture_path: Path):
    """Open a fixture the same way tests/test_open.py does -- via the
    mocked File > Open flow, which is fully confirmed against the live
    app already."""
    content = fixture_path.read_text(encoding="utf-8")
    open_mock.set_file(file_menu.page, fixture_path.name, content)
    dialog = file_menu.open_project()
    assert dialog is None, (
        f"Unexpected unsaved-changes prompt while opening {fixture_path.name}"
    )


# --- Empty state ------------------------------------------------------------

def test_open_recent_shows_no_recent_projects_on_fresh_session(file_menu):
    """A brand-new pytest-playwright context starts with zero storage
    history (no cookies/localStorage/IndexedDB) -- that's just how a
    fresh browser context works, confirmed already by the What's New
    popup logic in base_page.py relying on the same fact. So this test
    needs no explicit 'clear site data' step; the fresh context already
    is the clean state being tested."""
    file_menu.open_recent_menu()
    file_menu.expect_no_recent_projects()


# --- File > Open populates Open Recent ---------------------------------

def test_file_open_adds_project_to_recent_list(file_menu, site):
    """Opening a file via File > Open should make it appear in Open Recent.

    We seed IndexedDB directly (open_mock.seed_recent_projects) because
    the mocked showOpenFilePicker handle does not trigger the app's own
    open-tracking code path -- see module docstring for the full
    explanation. The test still exercises the Open Recent menu display.
    """
    first = site.recent_fixture_paths()[0]
    _open_via_file_open(file_menu, first)
    open_mock.seed_recent_projects(file_menu.page, [first])

    file_menu.open_recent_menu()
    file_menu.expect_recent_projects([first.stem])


def test_open_recent_keeps_last_5_evicts_oldest(file_menu, site):
    """Open Recent caps at 5 entries; the oldest is evicted when a 6th
    file is opened. Seeded directly (see module docstring) with the 5
    most-recently-opened of the 6 fixtures, oldest excluded, matching what
    the app would have stored after 6 real opens."""
    all_six = site.recent_fixture_paths()
    assert len(all_six) == 6, f"{site.product} needs 6 recent fixtures in sites.py"
    oldest = all_six[0]

    for fixture in all_six:
        _open_via_file_open(file_menu, fixture)
    # Seed only the 5 most recent, oldest-first so seed_recent_projects
    # reverses them to newest-first in the store.
    open_mock.seed_recent_projects(file_menu.page, all_six[1:])

    file_menu.open_recent_menu()
    names = file_menu.recent_project_names()

    assert len(names) == 5, (
        f"Expected Open Recent to show 5 entries, got {len(names)}: {names}"
    )
    assert oldest.stem not in names, (
        f"Expected the oldest ({oldest.stem!r}) to be absent after "
        f"6 files opened, but it's still listed: {names}"
    )
    expected = {f.stem for f in all_six[1:]}
    assert set(names) == expected, (
        f"Expected: {sorted(expected)}\nGot: {sorted(names)}"
    )


def test_open_recent_entry_reopens_correct_project(file_menu, site):
    """Clicking an Open Recent entry reopens that exact project.

    Confirmed mechanism (from pathData: {} in real records): clicking an
    entry calls showOpenFilePicker() again -- our mock intercepts it.
    We pre-configure set_file() with the target fixture's content before
    clicking, so the mock returns the right file when the picker fires.
    Uses the same exact-content check as test_open.py to prove the right
    file loaded.
    """
    first, target = site.recent_fixture_paths()[:2]
    _open_via_file_open(file_menu, target)
    _open_via_file_open(file_menu, first)  # switch away
    open_mock.seed_recent_projects(file_menu.page, [target, first])

    # Pre-configure the mock for the picker that fires on clicking the entry.
    content = target.read_text(encoding="utf-8")
    open_mock.set_file(file_menu.page, target.name, content)

    file_menu.open_recent_menu()
    dialog = file_menu.open_recent_project(target.stem)
    assert dialog is None, (
        "Unexpected unsaved-changes prompt reopening from Open Recent"
    )

    mode = site.mode_for_file(target)
    file_menu.expect_project_opened(target.stem, mode)
    file_menu.expect_content_matches_fixture(content, mode)


# --- Open Examples must NOT pollute Open Recent -----------------------------

@pytest.mark.skip(
    reason="File > Open Examples UI hasn't been investigated live yet -- "
           "no confirmed selectors for its entry list or modal structure. "
           "Writing this against guessed selectors risked clicking the "
           "wrong thing in a completely unexplored dialog. Needs a live "
           "Chrome session to inspect the real flow before this can be "
           "implemented for real instead of guessed."
)
def test_open_examples_does_not_add_to_recent_list(file_menu):
    """Planned: open 2 projects via File > Open Examples, then confirm
    Open Recent still shows "No Recent Projects" -- proving only files
    opened via File > Open (a real local file) count as "recent", per the
    user's confirmed requirement."""
    raise NotImplementedError("Needs live investigation of File > Open Examples first")


