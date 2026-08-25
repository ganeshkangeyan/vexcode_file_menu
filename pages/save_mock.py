"""
Mock for the browser's native File System Access API Save dialog.

Why this exists
----------------
File > Save (via the "Your project was never saved. Save now?" prompt) calls
window.showSaveFilePicker(), which opens the browser's real OS-level Save-As
window. No browser-automation tool (Playwright included) can drive a native
OS dialog: there is no CDP hook for it, the same way there's no hook for a
native "Open with..." menu. If that dialog is allowed to open for real
during a test, the test hangs forever waiting for a human to type a
filename and click Save.

The fix is to never let the real dialog open: we replace
window.showSaveFilePicker with a fake implementation *before* the page's own
scripts run (via page.add_init_script), so when the app calls it, it gets a
fake file handle back immediately. Everything happens in-memory, inside the
page, and we can read back exactly what filename and content the app tried
to save.

Confirmed real call sequence (captured from the live app by wrapping every
method with a diagnostic logger and triggering a real Save):

    1. showSaveFilePicker(options) -- options.suggestedName is
       "VEXcode Project.<ext>" (.v5blocks / .v5python / .v5cpp)
    2. handle.getFile()                       -- MUST exist, or the app's
       own try/catch surfaces a real "ERROR_SAVE_FF" dialog
       (TypeError: o.getFile is not a function) and Save silently fails.
    3. handle.queryPermission({writable: true, mode: "readwrite"})
    4. handle.createWritable({keepExistingData: true})  -- a "probe" stream,
       closed immediately without writing anything
    5. handle.createWritable({mode: "exclusive"})        -- the real stream
    6. writable.write(...) called TWICE on that stream:
         - once with a plain options object (no usable "data", something
           like {type: "truncate", size: N} -- a preallocation call)
         - once with a raw Uint8Array -- the actual file bytes
    7. writable.close()

A mock that only implements createWritable()/write()/close() (the first,
naive version of this file) breaks at step 2 -- the whole Save silently
fails inside the app's own error handling, and the test only sees "content
is None" with no indication why. Every method above must exist for the app
to get through its real save routine.

Dynamic filenames
------------------
The app always suggests a fixed default name ("VEXcode Project.<ext>"). To
satisfy the requirement that tests supply a filename at runtime instead of
hardcoding one, the mock checks window.__vexTestFileName first (set via
set_filename() below) and only falls back to the app's suggestedName if it
wasn't set. That value ultimately comes from the `project_name` pytest
fixture in conftest.py, which reads --project-name / VEX_PROJECT_NAME / a
timestamp default -- see README.
"""
from playwright.sync_api import Page

_INIT_SCRIPT = """
window.__vexSaveMock = { calls: [], savedFiles: [] };
window.__vexTestFileName = null;
window.__vexSaveDelay = 0;

async function __vexExtractText(data) {
    if (data == null) return null;
    if (typeof data === "string") return data;
    if (data instanceof Blob) return await data.text();
    if (data instanceof ArrayBuffer) return new TextDecoder().decode(data);
    if (ArrayBuffer.isView(data)) return new TextDecoder().decode(data);
    if (typeof data === "object") {
        // WriteParams-style call, e.g. {type: "truncate", size: N} (no
        // content) or {type: "write", data: ..., position: N}.
        if (data.type && data.type !== "write") return null;
        if ("data" in data) return await __vexExtractText(data.data);
    }
    return null;
}

function __vexMakeWritable(record) {
    return {
        write: async (data) => {
            const text = await __vexExtractText(data);
            if (text !== null) {
                record.content = (record.content || "") + text;
            }
        },
        seek: async () => {},
        truncate: async () => {},
        close: async () => {
            // Confirmed live (2026-08-23): with zero delay the app's own
            // status indicator flips "Saving..." -> "Saved" in ~10ms --
            // too fast for a human watching a headed run, or even a
            // MutationObserver-based assertion, to reliably observe
            // "Saving..." as its own state. Delaying the final close()
            // (rather than write()) keeps "Saving..." showing right up
            // until the save genuinely completes, without changing what
            // gets written. Default 0 preserves prior (instant) behavior
            // for every existing test.
            if (window.__vexSaveDelay) {
                await new Promise((resolve) => setTimeout(resolve, window.__vexSaveDelay));
            }
        },
    };
}

window.showSaveFilePicker = async (options) => {
    window.__vexSaveMock.calls.push(options || {});
    const fileName = window.__vexTestFileName
        || (options && options.suggestedName)
        || "untitled";

    const record = { name: fileName, content: null };
    window.__vexSaveMock.savedFiles.push(record);

    return {
        name: fileName,
        kind: "file",
        getFile: async () => new File([""], fileName),
        queryPermission: async () => "granted",
        requestPermission: async () => "granted",
        isSameEntry: async () => false,
        createWritable: async () => __vexMakeWritable(record),
    };
};
"""


def install(page: Page):
    """Install the mock. Must be called BEFORE page.goto(), so the fake
    showSaveFilePicker is in place before the app's own scripts load."""
    page.add_init_script(_INIT_SCRIPT)


def set_filename(page: Page, filename: str):
    """Set the filename the next Save call should use, overriding whatever
    default the app suggests."""
    page.evaluate("(name) => { window.__vexTestFileName = name; }", filename)


def set_save_delay(page: Page, ms: int):
    """Add an artificial delay (ms) to the mock's save-completion step,
    purely to make the transient "Saving..." status observable during a
    headed/live run or a status-transition assertion -- the real mocked
    save otherwise resolves in ~10ms, confirmed live to be faster than a
    human or a naive poll can reliably catch. Default 0 (unset) leaves
    every other test's timing unchanged."""
    page.evaluate("(ms) => { window.__vexSaveDelay = ms; }", ms)


def get_saved_files(page: Page) -> list:
    """Returns [{"name": ..., "content": ...}, ...] for every save the app
    completed (i.e. wrote data and closed the handle)."""
    return page.evaluate("window.__vexSaveMock.savedFiles")


def get_calls(page: Page) -> list:
    """Returns the raw options object the app passed to
    showSaveFilePicker() for every call, in order. Useful for asserting the
    suggested filename / accepted extension the app itself proposed."""
    return page.evaluate("window.__vexSaveMock.calls")
