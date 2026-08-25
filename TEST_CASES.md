# File Menu — Test Case Catalog

Status legend: **Automated** (in this repo, passing against the live DOM
structure as of the last verification pass) · **Proposed** (scoped, not yet
written).

## New Blocks Project / New Text Project — Automated

Source: `tests/test_file_menu.py`

| # | Test case | Expected result |
|---|---|---|
| 1 | File > New Blocks Project from a clean project | Canvas resets to the default single "when started" hat block; Download button visible; no Edit menu |
| 2 | File > New Text Project opens the language dialog | Dialog titled "Select a Project Language" shows Python and C++ options plus Cancel |
| 3 | Choosing Python | Editor switches to Python boilerplate (`from vex import *`, generated header comment); Errors panel shows |
| 4 | Choosing C++ | Editor switches to C++ boilerplate (`#include "vex.h"`, generated header comment); Errors panel shows |
| 5 | Cancelling the language dialog | Dialog closes; project/mode unchanged from before it opened |
| 6 | New Blocks Project after being in a text project | Cleanly switches back to blocks mode (regression case for mode-switch bugs) |

## Unsaved-changes Discard/Save prompt — Automated

Source: `tests/test_new_project_unsaved_changes.py`

Trigger: make an edit, then File > New Blocks Project. Verified this prompt
text/buttons are identical across all three source project types.

| # | Test case | Expected result |
|---|---|---|
| 7 | Discard, from a Blocks project with unsaved changes | "Your project was never saved. Save now?" prompt appears (Discard + Save only, no Cancel); Discard clears the workspace back to default |
| 8 | Save, from a Blocks project with unsaved changes | Save writes a dynamically-supplied filename (`<project_name>.v5blocks`) with non-empty content; workspace resets after |
| 9 | Discard, from a Python project with unsaved changes | Same prompt appears; Discard returns to a blank Blocks project |
| 10 | Save, from a Python project with unsaved changes | Save writes `<project_name>.v5python` with non-empty content |
| 11 | Discard, from a C++ project with unsaved changes | Same prompt appears; Discard returns to a blank Blocks project |
| 12 | Save, from a C++ project with unsaved changes | Save writes `<project_name>.v5cpp` with non-empty content |

Filenames are never hardcoded — see README "How the Save mock works" for how
the native OS Save dialog is avoided and how the filename is supplied at
runtime (`--project-name` / `VEX_PROJECT_NAME` / timestamped default).

## Open — Automated

Source: `tests/test_open.py`. Fixtures: three real project files in
`tests/fixtures/` (one per type — Blocks, Python, C++), not hand-crafted.

| # | Test case | Expected result |
|---|---|---|
| 13 | Open a real `.v5blocks` fixture | Toolbar project name updates to the filename; save status shows "Saved"; blocks mode shown; fixture's own content (workspace comment) visible |
| 14 | Open a real `.v5python` fixture | Same, in Python text mode; fixture's own code (e.g. `drivetrain.set_drive_velocity(...)`) visible |
| 15 | Open a real `.v5cpp` fixture | Same, in C++ text mode; fixture's own code (e.g. `AND Statement:`) visible |
| 16 | Open a file with unsupported/invalid content | Real "Unsupported project" error dialog appears; dismissing it leaves the current project untouched |
| 17 | Cancel the native picker (no file chosen) | No error, no change — current project stays exactly as it was |
| 18 | Open while there are unsaved changes | "Your project was never saved. Save now?" prompt appears first (same shared dialog as New Project); after Discard, the requested file loads normally |

See README "How the Open mock works" for how the native OS Open dialog is
avoided (`window.showOpenFilePicker()` mock) and why real fixture files are
used instead of minimal fakes.

## Rest of the File menu — Proposed, not yet automated

| Item | Test case ideas |
|---|---|
| Open Recent | Submenu lists previously opened files, most-recent-first; clicking an entry opens it; empty-list behavior on a fresh profile; list length cap |
| Open Examples | Examples browser opens; opening an example loads it correctly; closing leaves current project untouched |
| Save (Ctrl+S), standalone | Updates the "Not Saving" indicator; Ctrl+S shortcut matches the menu item; saving a brand-new/unnamed project |
| Save As, standalone | Downloaded/saved filename+extension matches current mode; renaming via this dialog updates the toolbar name; Cancel leaves project unchanged |
| What's New | Dialog opens with expected content; closes cleanly |
| About | Dialog opens with expected content; closes cleanly |
| Menu behavior (cross-cutting) | Menu closes on outside click; Escape closes the open menu; any items that should be disabled actually are |
| Unsupported-browser gate (Firefox) | Confirmed live (2026-08-26): loading the app in Firefox shows a real `.black_vca_lightbox` overlay -- "Web-based VEXcode V5 is not supported on this browser. Please use Google Chrome..." -- and everything else stays blocked behind it. Not a suite bug; a real app gate worth asserting on directly instead of just noting. See README "Running against other browsers" for the full investigation. |

## Explicitly out of scope for this round

- Pass/fail result reporting (JUnit XML / HTML report wiring) -- **done**: `pytest-html` wired up with automatic failure screenshots (`pytest_runtest_makereport` in `conftest.py`)
- TestPad integration (pushing results to TestPad, ID tagging)
- Edge browser support -- blocked on a launch failure specific to this dev machine (see README); not yet root-caused

TestPad integration is planned as a follow-up once the test cases above are reviewed.
