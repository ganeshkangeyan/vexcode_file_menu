"""
Common helpers shared by all page objects.

Note on locator strategy: the VEXcode V5 UI is a Blockly/canvas-based SPA
with no visible data-testid / id attributes on menu items, so locators here
are text-based (get_by_text / get_by_role with accessible name). This is the
most stable option available without instrumentation from the VEX team. If
they ever add data-testid hooks, swap these for page.get_by_test_id(...).
"""
from playwright.sync_api import Page, expect


class BasePage:
    # The "VEXcode V5 - What's New" dialog can appear automatically on load
    # (gated by a `v5version` localStorage flag -- shows once per new
    # version/fresh profile). It's the exact same dialog as File > What's
    # New, confirmed by inspecting the DOM: content lives in a
    # `.whatsnew_window` container. A fresh Playwright browser context has
    # no localStorage history, so this can show on every test run -- it
    # must be dismissed before anything else touches the page, or the first
    # real interaction (e.g. clicking File) will be blocked by the modal
    # overlay sitting on top of it.
    WHATS_NEW_ROOT_SELECTOR = ".whatsnew_window"

    def __init__(self, page: Page):
        self.page = page

    def highlight_and_click(self, locator, color: str = "red", pause_ms: int = 400, timeout=None):
        """Click `locator`, but first draw a thick colored outline around it
        and pause briefly so a human watching a headed/--slowmo run (or a
        recording) can actually see which element the test just chose --
        useful for menu items where several similarly-styled options sit
        next to each other. Purely visual: the outline is reverted right
        after the click, and nothing here changes what gets clicked or when
        Playwright considers the action complete.
        """
        try:
            locator.evaluate(
                "(el, color) => { el.dataset.vexPrevOutline = el.style.outline;"
                " el.dataset.vexPrevOutlineOffset = el.style.outlineOffset;"
                " el.style.outline = `4px solid ${color}`;"
                " el.style.outlineOffset = '2px'; }",
                color,
            )
        except Exception:
            pass  # purely cosmetic -- never let a highlight failure block the click
        self.page.wait_for_timeout(pause_ms)
        locator.click(timeout=timeout)
        try:
            locator.evaluate(
                "(el) => { el.style.outline = el.dataset.vexPrevOutline || '';"
                " el.style.outlineOffset = el.dataset.vexPrevOutlineOffset || ''; }"
            )
        except Exception:
            pass

    @property
    def whats_new_popup(self):
        return self.page.locator(self.WHATS_NEW_ROOT_SELECTOR)

    def _close_whats_new(self):
        self.whats_new_popup.get_by_role("button", name="Close", exact=True).click()

    def auto_dismiss_whats_new(self):
        """Close the auto-shown What's New popup whenever it appears, not
        just if it's there in the first few seconds. Confirmed (2026-10-24,
        V5/EXP/IQ): on a slow load it can pop up well after the app looks
        ready, then blocks every click for the rest of the test. Playwright
        checks for it before each action/assertion and closes it first.
        Turned off again by open_whats_new(), which opens the same dialog
        on purpose."""
        self.page.add_locator_handler(self.whats_new_popup, self._close_whats_new)

    def stop_auto_dismissing_whats_new(self):
        self.page.remove_locator_handler(self.whats_new_popup)

    def wait_until_loaded(self):
        """Wait for the app shell to finish booting, with the What's New
        popup auto-closed whenever it shows up (now or later in the test).

        Don't also close it by hand here: confirmed (2026-10-24) that a
        manual Close click while the handler is registered races it -- the
        handler fires first, closes the popup, and the manual click then
        waits 30s for a Close button that's gone."""
        self.auto_dismiss_whats_new()
        # 60s: confirmed (2026-11-25, 123) that a slow load can take over 30s.
        expect(self.page.get_by_text("File", exact=True)).to_be_visible(timeout=60000)
