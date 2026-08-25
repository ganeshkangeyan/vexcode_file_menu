"""
Mock for the browser's native File System Access API Open dialog.

Why this exists
----------------
File > Open calls window.showOpenFilePicker(), the read counterpart to the
showSaveFilePicker() used by Save -- same native OS-level picker, same
reason it can't be automated directly (see save_mock.py for the full
explanation; it applies identically here).

Confirmed real call sequence (captured from the live app the same way as
Save's -- wrap every method, trigger a real Open):

    1. showOpenFilePicker(options) -- options.types accepts ALL THREE
       extensions in one picker: .v5blocks, .v5cpp, .v5python (unlike Save,
       which is called once per project type with just that type's
       extension).
    2. handle.queryPermission({writable: true, mode: "readwrite"})
    3. handle.createWritable(...)  -- called but nothing is written; the
       app appears to reuse the same permission-check code path as Save.
    4. handle.getFile()  -- called twice, returns a real File object which
       the app reads (presumably via .text()) to get the JSON project
       payload.

Confirmed error path: if the read content doesn't look like a valid
VEXcode V5 project, the app shows a real dialog: "Unsupported project -
The selected project file is for a different version of VEXcode. Please
select a VEXcode V5 project file." -- exact text, with an OK button.

Confirmed success path (verified end-to-end with a real fixture file):
opening a valid project updates the toolbar project name, flips the save
status indicator to "Saved", switches Blocks/Text mode to match the file,
loads the actual code/blocks, and applies the file's robotConfig (e.g. a
Drivetrain in the config makes a "Drivetrain" section appear in the
snippet/block palette).

Usage
-----
Unlike Save (which is always triggered by the app with its own default
filename), Open needs the test to supply what "file" the fake picker
should return before triggering File > Open:

    open_mock.set_file(page, "MyProject.v5blocks", fixture_content)
    file_menu.open_project()

If no file is configured, the mock rejects with AbortError -- the same
outcome as a real user cancelling the native picker -- so that's the
default behavior for the "cancel" test case, no extra setup needed.

Why the returned handle inherits from the real FileSystemFileHandle
---------------------------------------------------------------------
First version of this mock returned a plain JS object shaped like a
handle (getFile/queryPermission/etc. as own properties, no real
prototype). Opening a file through it worked completely -- content
loaded, project name/mode/save-status all updated correctly -- but the
opened file never showed up in File > Open Recent, confirmed live via a
diagnostic dump (2026-08-21: "No Recent Projects" was still showing after
a real, successful open through this mock).

Working theory: apps typically persist a real `FileSystemFileHandle` to
IndexedDB to build a "recent files" list -- that's specifically what
handles support that a plain object doesn't. A plain object was never
going to look like a real handle to any check the app does before
deciding whether to persist it.

The fix: build the fake handle via
`Object.create(FileSystemFileHandle.prototype)` instead of a plain object
literal, so `handle instanceof FileSystemFileHandle` is true. `kind` and
`name` are real *readonly accessor* properties on that prototype (no
setter), so they're set via `Object.defineProperty` rather than plain
assignment, which could silently no-op or throw against an inherited
getter with no setter. The method overrides (getFile, queryPermission,
etc.) are ordinary writable properties on the real prototype, so plain
assignment correctly shadows them with our fake implementations.

Whether this is actually enough is genuinely unconfirmed as of writing --
if the app's recent-tracking depends on the browser engine's own internal
handle-serialization machinery (not just an instanceof check in JS), this
won't be sufficient, since that's implemented below the JS layer and can't
be faked from here. Needs a real pytest run to know for sure.
"""
from playwright.sync_api import Page

_INIT_SCRIPT = """
window.__vexOpenMock = { calls: [] };
window.__vexOpenFile = null;  // set via set_file(): { name, content }
// Opt-in escape hatch for manual diagnostics only (see
// enable_real_picker_passthrough() below) -- lets a human click through
// the REAL native Open dialog once, for things no JS-level mock can ever
// produce (e.g. capturing what a real "recent" IndexedDB record looks
// like). False for every normal automated test; none of them set this.
window.__vexOpenPassthrough = false;
window.__vexRealShowOpenFilePicker = window.showOpenFilePicker
    ? window.showOpenFilePicker.bind(window)
    : undefined;

window.showOpenFilePicker = async (options) => {
    window.__vexOpenMock.calls.push(options || {});

    if (!window.__vexOpenFile) {
        if (window.__vexOpenPassthrough && window.__vexRealShowOpenFilePicker) {
            // Fall through to the browser's real native picker -- only
            // reachable when a test explicitly opts in.
            return window.__vexRealShowOpenFilePicker(options);
        }
        // No file configured -- behave like the user cancelled the native
        // picker, same as a real showOpenFilePicker() rejection.
        throw new DOMException("The user aborted a request.", "AbortError");
    }

    const { name, content } = window.__vexOpenFile;
    const file = new File([content], name, { type: "text/plain" });

    // Build on the REAL FileSystemFileHandle prototype when available, so
    // `handle instanceof FileSystemFileHandle` is true -- see the module
    // docstring "Why the returned handle inherits from the real
    // FileSystemFileHandle" for why this was added. Falls back to a plain
    // object if the browser doesn't expose that global at all.
    const handle = (typeof FileSystemFileHandle !== "undefined")
        ? Object.create(FileSystemFileHandle.prototype)
        : {};

    // kind/name are readonly accessor properties on the real prototype
    // (getter only, no setter) -- defineProperty creates a genuine own
    // data property that shadows the inherited getter, where a plain
    // `handle.kind = "file"` assignment could silently no-op or throw.
    Object.defineProperty(handle, "kind", { value: "file", enumerable: true, configurable: true });
    Object.defineProperty(handle, "name", { value: name, enumerable: true, configurable: true });

    // These are ordinary writable methods on the real prototype, so plain
    // assignment correctly creates shadowing own properties here.
    handle.getFile = async () => file;
    handle.queryPermission = async () => "granted";
    handle.requestPermission = async () => "granted";
    handle.isSameEntry = async () => false;
    handle.createWritable = async () => ({
        write: async () => {},
        seek: async () => {},
        truncate: async () => {},
        close: async () => {},
    });

    return [handle];
};
"""


def install(page: Page):
    """Install the mock. Must be called BEFORE page.goto(), same as
    save_mock.install() -- see that module for why."""
    page.add_init_script(_INIT_SCRIPT)


def set_file(page: Page, filename: str, content: str):
    """Configure what the next File > Open call should return, as if the
    user had picked this exact file in the native dialog."""
    page.evaluate(
        "(f) => { window.__vexOpenFile = f; }",
        {"name": filename, "content": content},
    )


def clear_file(page: Page):
    """Reset to 'no file configured', so the next Open simulates the user
    cancelling the picker. Not required between tests (each test gets a
    fresh page), but useful within a single test that needs to exercise
    both a cancel and then a real open."""
    page.evaluate("window.__vexOpenFile = null")


def enable_real_picker_passthrough(page: Page):
    """DIAGNOSTIC USE ONLY -- not for regular automated tests. Makes the
    next File > Open (with no file configured via set_file()) fall
    through to the browser's REAL native showOpenFilePicker() instead of
    simulating a cancel. Requires a human to actually be watching the
    headed browser and click through the real OS file dialog -- Playwright
    still can't drive that dialog itself, this just gets out of the way so
    a person can. See tests/test_open_recent.py's
    test_zzz_diagnostic_manual_capture_real_recent_record for why this
    exists: it's the only way to observe a real "recent" IndexedDB record,
    since our mocked handle can never be written to that store (structured
    clone can't serialize function properties -- see this module's
    docstring)."""
    page.evaluate("window.__vexOpenPassthrough = true")


def get_calls(page: Page) -> list:
    """Raw options passed to showOpenFilePicker() for every call, in
    order. Useful for asserting the accepted extensions."""
    return page.evaluate("window.__vexOpenMock.calls")


def seed_recent_projects(page: Page, fixture_paths):
    """Write records directly into IndexedDB's recent-projects-store.

    Confirmed record format (2026-08-23, captured from a real pytest run
    using the manual passthrough diagnostic -- see
    test_zzz_diagnostic_manual_capture_real_recent_record):

        key:   "recent-projects-key"
        value: array, newest-first, each entry:
               {
                 "fileRef": {
                   "name": "<stem, no extension>",
                   "pathData": {},
                   "fileExtension": "<ext without dot>",
                   "hasWritePermission": true,
                   "hasFolderWritePermissions": true
                 },
                 "lastOpened": <unix ms timestamp>
               }

    pathData is always {} in real records -- the app stores only file
    metadata, not the FileSystemFileHandle itself. This means clicking an
    Open Recent entry calls showOpenFilePicker() again (our mock
    intercepts it), rather than reopening via a stored handle.

    fixture_paths: iterable of Path objects, ordered oldest-first.
    Reversed here so the stored array is newest-first, matching real
    app behavior. Must be called AFTER page.goto() (IndexedDB is
    domain-scoped and not accessible until the page loads).
    """
    import time as _time
    base_ms = int(_time.time() * 1000)
    records = [
        {
            "fileRef": {
                "name": p.stem,
                "pathData": {},
                "fileExtension": p.suffix.lstrip("."),
                "hasWritePermission": True,
                "hasFolderWritePermissions": True,
            },
            "lastOpened": base_ms + i,
        }
        for i, p in enumerate(fixture_paths)
    ]
    records.reverse()  # newest-first, matching real app behavior

    page.evaluate(
        """
        async (records) => {
            const db = await new Promise((resolve, reject) => {
                const req = indexedDB.open('project-storage-db', 1);
                req.onupgradeneeded = (e) => {
                    const db = e.target.result;
                    if (!db.objectStoreNames.contains('recent-projects-store')) {
                        db.createObjectStore('recent-projects-store');
                    }
                };
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => reject(req.error);
            });
            await new Promise((resolve, reject) => {
                const tx = db.transaction('recent-projects-store', 'readwrite');
                const store = tx.objectStore('recent-projects-store');
                store.put(records, 'recent-projects-key');
                tx.oncomplete = () => resolve();
                tx.onerror = () => reject(tx.error);
            });
            db.close();
        }
        """,
        records,
    )
