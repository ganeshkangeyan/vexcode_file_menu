# VEXcode V5 — File Menu Regression Suite

Playwright + pytest, Page Object Model. Targets prod: `https://codev5.vex.com/`.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Run

```bash
pytest
```

Runs headed Chromium by default (set in `conftest.py`). To run headless, edit
`browser_type_launch_args` in `conftest.py` and set `"headless": True`.

Target a different environment (e.g. staging) without editing files:

```bash
pytest --base-url=https://staging.codev5.vex.com/
```

Run the whole suite against multiple VEX product sites in one command (they
share this File menu design, so nothing in `pages/` or `tests/` is specific
to codev5.vex.com):

```bash
pytest --sites="https://codev5.vex.com/,https://codeexp.vex.com/"
# or
VEX_SITES="https://codev5.vex.com/,https://codeexp.vex.com/" pytest
```

Every test runs once per site automatically (e.g.
`test_new_blocks_project_resets_to_blank_blocks_canvas[https://codeexp.vex.com/-chromium]`).
With zero or one site given, this is a no-op and `--base-url` behaves
exactly as before.

Give Save-flow tests a specific filename instead of the timestamped default:

```bash
pytest --project-name=MyRegressionRun
# or
VEX_PROJECT_NAME=MyRegressionRun pytest
```

## Running a subset with markers

Every `tests/test_*.py` file carries a module-level `pytestmark` for its File
menu feature area (registered in `pytest.ini`, `--strict-markers` enabled so a
typo in `-m` fails loudly instead of silently matching nothing):

```bash
pytest -m save_as          # just File > Save As
pytest -m "about or whats_new"   # About + What's New only
pytest --markers            # list all registered markers with descriptions
```

Available markers: `new_project`, `unsaved_changes`, `open`, `open_recent`,
`open_examples`, `save`, `save_as`, `whats_new`, `about`.

## Running against other browsers

`pytest.ini` deliberately does **not** hardcode `--browser=chromium` in
`addopts` -- pytest-playwright's `--browser` flag is *additive*
(`action="append"`), not an override. Confirmed live (2026-08-25): with
`--browser=chromium` baked into `addopts`, passing another `--browser=...` on
the CLI ran the suite against **two** browser instances (`chromium0`/
`chromium1`) instead of replacing the default, and one of them crashed. With
nothing hardcoded, omitting `--browser` entirely gets pytest-playwright's own
default (Chromium) with zero flags, and passing exactly one `--browser=...`
on the CLI is the only browser that runs.

```bash
pytest                                              # Chromium (default)
pytest --browser=firefox                            # Firefox
pytest --browser=chromium --browser-channel=msedge   # Edge (Chromium engine, msedge channel)
```

**Known cross-browser limitations, confirmed live (2026-08-25/26) -- not bugs
in this suite:**

- **Firefox cannot run VEXcode V5 at all.** The app itself shows a real,
  intentional gate on load: `.black_vca_lightbox` containing *"Web-based
  VEXcode V5 is not supported on this browser. Please use Google Chrome to
  use the web-based VEXcode V5 site."* Every File-menu click after that just
  times out retrying against the permanent overlay -- confirmed by isolating
  the exact same test file on Chromium alone (3/3 passed) vs. Firefox alone
  (3/3 failed on the identical overlay). This is correct app behavior, not a
  suite defect. **Proposed follow-up test case** (not yet written): load the
  app in Firefox and assert the gate message appears -- turns this known
  limitation into an actual regression check instead of just a note.
- **Edge failed to launch in this environment.** `--browser=chromium
  --browser-channel=msedge` against the system-installed Edge
  (`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`) produces
  `TargetClosedError: Target page, context or browser has been closed` --
  the process launches (has a PID) and exits immediately (`exitCode=0`), so
  it isn't a suite/selector problem. `playwright install msedge` refused to
  proceed non-destructively (it would require removing the existing system
  Edge installation first via `--force`, which was deliberately NOT run here
  since it would touch the machine's real, in-use browser). Unresolved --
  needs either a machine with a Playwright-managed Edge already present, or
  an explicit decision to `--force` reinstall.
- **Clipboard-permission grants are Chromium-only in Playwright.**
  `browser_context_args` used to unconditionally request
  `["clipboard-read", "clipboard-write"]` context permissions (needed for
  `FileMenuPage.get_editor_full_text()`'s exact-content checks). Confirmed
  live: on Firefox this hard-errors `Browser.new_context` with `Unknown
  permission: clipboard-read`, breaking **every** test's context creation,
  not just the clipboard-using ones. Fixed in `conftest.py` by only
  requesting those permissions when `browser_name == "chromium"` (which
  covers Edge too, since it runs on the Chromium engine) -- but the
  clipboard-dependent assertions themselves (`test_open.py`'s Python/C++
  fixture content checks) are still Chromium/Edge-only until a
  non-clipboard fallback is written for other engines.

## Jenkins / CI invocation

Combine site, marker, and browser selection into one command a Jenkins job
parameterizes (e.g. string parameters `SITES`, `SUITE`, `BROWSER`):

```bash
pytest \
  -m "${SUITE}" \
  --sites="${SITES}" \
  --browser=chromium \
  --html=report.html --self-contained-html
```

Example concrete invocations:

```bash
# Save/Save As only, against two sites, Chromium
pytest -m save_as --sites="https://codev5.vex.com/,https://code123.vex.com/" \
  --html=report.html --self-contained-html

# Everything, single site, Edge
pytest --sites="https://codev5.vex.com/" --browser=chromium \
  --browser-channel=msedge --html=report.html --self-contained-html
```

A screenshot is auto-attached to `report.html` for any failing test (see
`pytest_runtest_makereport` in `conftest.py`) -- useful as a build artifact
in Jenkins even without further wiring.

## What's covered

- `tests/test_file_menu.py` — File > New Blocks Project, File > New Text
  Project (Python / C++ / Cancel), and the mode-switch case (text → blocks).
- `tests/test_new_project_unsaved_changes.py` — the "Your project was never
  saved. Save now?" Discard/Save prompt that appears when File > New Blocks
  Project is triggered while there are unsaved changes, for Blocks, Python,
  and C++ source projects (Discard clears the workspace; Save writes a
  dynamically-supplied filename).
- `tests/test_open.py` — File > Open: loading each of the three real
  project types from disk, the "Unsupported project" error on invalid
  content, cancelling the native picker, and the Discard/Save prompt
  interaction when there are unsaved changes.

## Project layout

```
conftest.py                    # fixtures: browser/page, project_name, file_menu
pages/
  base_page.py                  # shared BasePage (wait_until_loaded)
  file_menu_page.py             # FileMenuPage, NewProjectLanguageDialog,
                                 # UnsavedChangesDialog
  save_mock.py                  # native Save-dialog mock (see below)
  open_mock.py                  # native Open-dialog mock (see below)
tests/
  test_file_menu.py             # New Project regression tests
  test_new_project_unsaved_changes.py  # Discard/Save prompt tests
  test_open.py                  # File > Open tests
  fixtures/                     # real .v5blocks/.v5python/.v5cpp files used by test_open.py
```

## Locator strategy

The app is a Blockly/canvas SPA with no `data-testid` hooks on menu items,
so locators are text/role-based (`get_by_text`, `get_by_role(name=...)`),
matched against the *real* DOM/accessible text confirmed by inspecting the
live app — not just how it looks on screen. Two things bit us during
development and are worth knowing before adding more locators:

- **CSS text-transform lies.** The Download button reads "DOWNLOAD" on
  screen but its real accessible name is `"Download"` (mixed case) —
  `text-transform: uppercase` is styling, not content. Always verify the
  real accessible name (e.g. via the browser's accessibility tree) rather
  than reading it off a screenshot.
- **Duplicate/hidden elements break exact-text matches.** This app keeps
  several off-screen or unrelated elements in the DOM with identical text to
  what you're trying to click — e.g. a hidden "Convert to Text" feature also
  has "Python"/"C++" buttons, and an unrelated project-rename dropdown also
  has its own "Cancel" and "Save" buttons, all simultaneously present
  (and even simultaneously *visible* by bounding-box, just positioned
  elsewhere) alongside the ones you actually want. An unscoped
  `get_by_text`/`get_by_role` will hit Playwright's strict-mode violation
  ("resolved to N elements") on these. The fix used throughout
  `file_menu_page.py` is to scope dialog locators to the modal's own
  container (`.prompt_window`) rather than searching the whole page.
- **A fresh project genuinely renders two overlapping "when started" hat
  blocks**, confirmed via a real fresh Playwright browser context, not just
  leftover state from manual testing -- both are separate top-level blocks
  in Blockly's own model (`.blocklyDraggable`), not a stroke/fill text
  rendering duplicate. `default_blocks_hat` uses `.first` since the tests
  only need to confirm blocks-mode is showing, not how many hat blocks
  exist.
- Same CSS-uppercase trap hit the **Build** button (only visible in
  text/code editor mode) as hit Download -- real accessible name is
  `"Build"`.

If test IDs get added later, swap to `get_by_test_id(...)` — the page
objects centralize every locator so that's a one-file change.

## The "What's New" popup on load

`https://codev5.vex.com/` can show a "VEXcode V5 - What's New" modal
automatically on load — gated by a `v5version` value in `localStorage`
(shown once per new version / fresh profile). It's the identical dialog
content as File > What's New, just auto-triggered. Since every pytest run
gets a brand-new browser context with no `localStorage` history, this can
appear on **every single test run**, and if left unhandled it sits on top
of the page and blocks the first real interaction (e.g. clicking File).

`BasePage.wait_until_loaded()` (called by the `file_menu` fixture on every
test) checks for it first and clicks Close before doing anything else. The
dialog's Close button is scoped to its own container (`.whatsnew_window`)
because — same pattern as everywhere else in this app — there's a second,
hidden "Close" button elsewhere in the DOM with identical text that an
unscoped locator would also match.

## How the Save mock works

File > Save (via the "Save now?" prompt) calls the browser's native
`window.showSaveFilePicker()`, which opens a real OS-level Save-As window.
No browser-automation tool — Playwright included — can drive that dialog:
there's no CDP hook into native OS windows, so if it's allowed to open for
real, the test just hangs waiting for a human to type a filename.

`pages/save_mock.py` avoids this instead of fighting it: `save_mock.install(page)`
(called in the `file_menu` fixture, before `page.goto()`) replaces
`window.showSaveFilePicker` with a fake implementation *before* the app's
own scripts run. When the app calls it, it gets a fake file handle back
immediately — the native dialog never opens — and the mock records the
filename and content the app tried to write, readable back via
`save_mock.get_saved_files(page)`.

Confirmed real call shape per project type (captured directly from the live
app):

| Project | Suggested filename | Extension |
|---|---|---|
| Blocks | `VEXcode Project.v5blocks` | `.v5blocks` |
| Python | `VEXcode Project.v5python` | `.v5python` |
| C++ | `VEXcode Project.v5cpp` | `.v5cpp` |

The app always suggests that fixed name. To supply a filename dynamically
instead of hardcoding one, call `save_mock.set_filename(page, name)` before
clicking Save — the mock uses that name instead of the app's default. Tests
get the name from the `project_name` fixture (`--project-name` CLI flag →
`VEX_PROJECT_NAME` env var → timestamped default), so runs never collide on
a hardcoded filename.

## How the Open mock works

File > Open calls the browser's native `window.showOpenFilePicker()` — the
read counterpart to Save's `showSaveFilePicker()`, same native-OS-dialog
problem, same fix. `pages/open_mock.py` replaces it via
`open_mock.install(page)` (called in the `file_menu` fixture, before
`page.goto()`), so the app never opens a real picker.

Because Open reads a file rather than writing one, tests must tell the mock
*what* to "return" before triggering File > Open:

```python
open_mock.set_file(page, "MyProject.v5blocks", file_content)
file_menu.open_project()
```

If no file is configured, the mock rejects with `AbortError` — the same
outcome as a real user closing the picker without choosing anything — so
that's the default behavior, useful for the cancel test case with no extra
setup.

Confirmed real call shape (captured the same way as Save's, by wrapping
every method with a diagnostic logger and triggering a real Open):
`showOpenFilePicker()` is called once with all three extensions accepted in
a single picker (unlike Save, which is per-type), then the app calls
`queryPermission()`, `createWritable()` (unused but must exist), and
`getFile()` on the returned handle to read the file's contents.

Test fixtures (`tests/fixtures/`) are three real project files, not
hand-crafted ones — exported from the app itself, one per project type:
`Printing Lines and Shapes.v5blocks`, `Changing Velocities.v5python`,
`Complex Decisions (AND OR NOT).v5cpp`. Opening real files (rather than a
minimal fake payload) exercises the actual JSON project envelope format,
including `robotConfig` (e.g. the C++ fixture's Drivetrain + two Bumpers).

On success the app updates the toolbar project name (`input.for_name`) and
save-status indicator (`.project_saving_status`, flips to `"Saved"`), and
switches Blocks/Text mode to match the file — asserted together by
`file_menu.expect_project_opened(name, mode)`. On invalid content (not a
real VEXcode V5 project) the app shows a real "Unsupported project" error
dialog, asserted by `file_menu.expect_unsupported_project_error()`.

### Proving the *right* file loaded, not just *a* file

Name/status/mode checks alone don't rule out the wrong or stale content
loading under a correct-looking name. `test_open.py` also does an
exact-content check against each fixture's real source, using two methods
on `FileMenuPage` built after investigating what's actually readable back
from the live app:

- **`get_blocks_workspace_xml()`** — `Blockly.getMainWorkspace()` is a real
  global on this app (confirmed live), and
  `Blockly.Xml.workspaceToDom()` + `domToText()` is the exact same
  serialization the app's own Save flow produces. The test extracts the
  full `<block type="...">` sequence from both the loaded workspace and
  the fixture's own `workspace` XML and asserts they're identical —
  proving the specific blocks that rendered match the specific file
  requested.
- **`get_editor_full_text()`** — for Python/C++. Confirmed live that this
  app does **not** expose `window.monaco` (or any other global handle to
  the editor), and Monaco's DOM is virtualized — only the lines currently
  scrolled into view actually exist as text nodes, so `get_by_text()` can
  only ever see a fragment of a real file. The reliable path is
  select-all (Ctrl+A) → copy (Ctrl+C) → `navigator.clipboard.readText()`,
  which reads back the *entire* file exactly as loaded. Requires the
  `clipboard-read`/`clipboard-write` permissions granted in
  `browser_context_args` (see `conftest.py`).

An earlier version of these tests just checked that one marker string was
visible somewhere on the page — weak, and for the Blocks fixture that
marker was a workspace *comment* whose on-canvas visibility was never
actually confirmed. The exact-content checks above replace that.

## Extending this suite

The File menu has more items we surveyed but haven't automated yet:

- **Open Recent** — submenu populated from the user's/browser's local
  history; not fully deterministic in a clean test browser context (list is
  empty on a fresh profile), so seed it first via Open, or mock the
  underlying storage.
- **Open Examples** — opens an examples browser; add a page object once the
  scope is defined (which examples, what to assert).
- **Save (Ctrl+S) / Save As on their own** (i.e. not via the Discard/Save
  prompt) — same native-dialog problem, same `save_mock` fixture should
  cover it; not yet written as standalone tests.
- **What's New / About** — simple info dialogs; same pattern as
  `NewProjectLanguageDialog`, just assert dialog text and a close action.

Add each as its own page-object class in `pages/file_menu_page.py` (or a new
`pages/` module if it grows large), and a matching `tests/test_*.py` file.

Pass/fail reporting and TestPad integration are deliberately out of scope
for this round — see `TEST_CASES.md` for the full catalog of what's
automated vs. still proposed.
