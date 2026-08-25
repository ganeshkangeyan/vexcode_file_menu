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

    def highlight_and_click(self, locator, color: str = "red", pause_ms: int = 400):
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
        locator.click()
        try:
            locator.evaluate(
                "(el) => { el.style.outline = el.dataset.vexPrevOutline || '';"
                " el.style.outlineOffset = el.dataset.vexPrevOutlineOffset || ''; }"
            )
        except Exception:
            pass

    def dismiss_whats_new_if_present(self):
        whats_new = self.page.locator(self.WHATS_NEW_ROOT_SELECTOR)
        try:
            expect(whats_new).to_be_visible(timeout=3000)
        except AssertionError:
            return  # didn't show this run -- nothing to do
        whats_new.get_by_role("button", name="Close", exact=True).click()
        expect(whats_new).not_to_be_visible(timeout=5000)

    def wait_until_loaded(self):
        """Wait for the app shell to finish booting, dismissing the
        What's New dialog first if it showed up on this load."""
        self.dismiss_whats_new_if_present()
        expect(self.page.get_by_text("File", exact=True)).to_be_visible(timeout=15000)
