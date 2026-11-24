"""
Page object for File > Open Examples -- the built-in examples browser.

All selectors confirmed against the live app (codev5.vex.com) via direct
Playwright DOM inspection on 2026-08-23. Key findings:

  - Panel root:    div.scene_portal > div.scene_wrapper
  - Title:         span.title  (text "Choose a Blocks example project")
  - Back button:   button#scene_back_button  (inner text "< Back")
  - Category tabs: div.filterbutton inside div.filterbar  -- must be scoped
                   to .filterbar because "Sensing" also matches a
                   .blocklyToolboxCategory in the Blockly panel (same page DOM)
  - Active tab:    adds class "active" to the filterbutton div
  - Project cards: div.sample_file_btn  (count per product: see sites.py)
  - Card name:     div.label inside each card (plain text, no extension)
  - Yellow note:   textarea.blocklyCommentTextarea -- its .value (not
                   .innerText, which is always empty) starts with the
                   project name, in one of three formats depending on the
                   product (confirmed live 2026-10-24):
                       V5 / EXP:  "Project: \\n{name}\\n\\nDescription: ..."
                       123 / GO:  "Project: {name} \\n\\nDescription: ..."
                       IQ:        "Project Name: {name}\\n\\nDescription: ..."
                   The textarea lives in the main document via a Blockly
                   SVG <foreignObject> -- confirmed reachable via
                   page.evaluate() in the main frame context.

The category tabs and card count differ per product and come from the
SiteConfig (sites.py); everything else here is the same on every product.
"""
import re

from playwright.sync_api import Page, expect

from pages.base_page import BasePage
from sites import SiteConfig

# "Project:" or "Project Name:", then the name -- on the same line or the next.
_NOTE_NAME_RE = re.compile(r"^Project(?: Name)?:[ \t]*\n?[ \t]*(\S[^\n]*?)[ \t]*$", re.MULTILINE)


class OpenExamplesPage(BasePage):
    BLOCKS_TITLE_TEXT = "Choose a Blocks example project"

    def __init__(self, page: Page, site: SiteConfig):
        super().__init__(page)
        self.site = site

    @property
    def title(self):
        # Confirmed: <span class="title">Choose a Blocks example project</span>
        return self.page.locator("span.title", has_text=self.BLOCKS_TITLE_TEXT)

    @property
    def back_button(self):
        # Confirmed: <button id="scene_back_button" class="vcj back_btn active">
        # Inner text is "< Back" (not just "Back") -- the arrow is part of the text.
        return self.page.locator("#scene_back_button")

    @property
    def filterbar(self):
        # Confirmed: <div class="filterbar flex_row"> containing all filterbutton divs
        return self.page.locator(".filterbar")

    @property
    def project_cards(self):
        # Confirmed: <div class="sample_file_btn flex_column">
        return self.page.locator(".sample_file_btn")

    def category_tab(self, name: str):
        # Scoped to .filterbar -- required to avoid the "Sensing" collision with
        # a .blocklyToolboxCategory element that also contains text "Sensing".
        return self.filterbar.locator(".filterbutton", has_text=re.compile(f"^{re.escape(name)}$"))

    def expect_visible(self):
        expect(self.title).to_be_visible(timeout=10000)
        # Brief pause so the full grid renders and is visible to a human
        # watching the headed browser, not just confirmed present in the DOM.
        self.page.wait_for_timeout(800)

    def expect_not_visible(self):
        expect(self.title).not_to_be_visible(timeout=10000)

    def go_back(self):
        """Click the Back button -- closes the examples browser."""
        self.back_button.click()
        self.expect_not_visible()
        self.page.wait_for_timeout(500)

    def expect_all_category_tabs_present(self):
        """Assert every category tab this product has is visible in the filter bar."""
        for name in self.site.example_categories:
            expect(self.category_tab(name)).to_be_visible(timeout=5000), \
                f"Category tab '{name}' not visible in the filter bar"

    def click_category(self, name: str):
        """Click a category filter tab and wait for the card list to update."""
        self.category_tab(name).click()
        # Wait until this tab is marked active before returning.
        expect(
            self.filterbar.locator(".filterbutton.active", has_text=re.compile(f"^{re.escape(name)}$"))
        ).to_be_visible(timeout=5000)
        # Pause so a human watching the headed browser can actually see the
        # grid change from one category to the next -- the default slow_mo
        # delay (see conftest.py) applies before each Playwright action, not
        # after the resulting UI update settles, so without this the grid
        # can flip faster than it's readable.
        self.page.wait_for_timeout(800)

    def visible_card_count(self) -> int:
        # The grid shows "Loading..." for a moment after switching tabs --
        # confirmed (2026-10-24, GO) that counting straight away can see 0
        # cards in a category that has some. Wait for a card first; a
        # genuinely empty category still returns 0 after the timeout.
        try:
            expect(self.project_cards.first).to_be_visible(timeout=15000)
        except AssertionError:
            pass
        return self.project_cards.count()

    def tab_names(self) -> list:
        """The category tabs actually shown in the filter bar, in order."""
        expect(self.filterbar.locator(".filterbutton").first).to_be_visible(timeout=10000)
        return [t.strip() for t in self.filterbar.locator(".filterbutton").all_inner_texts()]

    def card_names(self) -> list:
        """Names of every card in the current tab, in grid order. Waits for
        the card count to stop changing first, so a grid that's still
        filling in isn't read half-way."""
        self.visible_card_count()
        previous, stable_reads = -1, 0
        for _ in range(20):
            count = self.project_cards.count()
            stable_reads = stable_reads + 1 if count == previous else 0
            if stable_reads >= 2:
                break
            previous = count
            self.page.wait_for_timeout(250)
        return [n.strip() for n in self.project_cards.locator(".label").all_inner_texts()]

    def catalog(self) -> dict:
        """Every tab and the example names under it: {tab: [names]}, in
        on-screen order. Ends with the "All" tab selected again."""
        result = {}
        for tab in self.tab_names():
            self.click_category(tab)
            result[tab] = self.card_names()
        if "All" in result:
            self.click_category("All")
        return result

    def template_names(self) -> set:
        """Names of the examples under the Templates tab ("" set if the
        product has no Templates tab). Leaves the "All" tab selected."""
        if "Templates" not in self.site.example_categories:
            return set()
        self.click_category("Templates")
        self.visible_card_count()  # wait for the grid
        names = {n.strip() for n in self.project_cards.locator(".label").all_inner_texts()}
        self.click_category("All")
        return names

    def index_of_nth_project(self, n: int) -> int:
        """Index (in the "All" grid) of the n-th example that is a real
        project rather than a Template. Templates are blank worksheets --
        confirmed on IQ (2026-10-24) their yellow note starts "Name: / Date:
        / Class:" with no project name, so the name-match check doesn't
        apply to them."""
        templates = self.template_names()
        self.visible_card_count()  # wait for the "All" grid
        names = [n.strip() for n in self.project_cards.locator(".label").all_inner_texts()]
        projects = [i for i, name in enumerate(names) if name not in templates]
        return projects[n]

    def get_card_name(self, index: int) -> str:
        """Read the project name shown below the image for the Nth card (0-based).
        Confirmed: <div class="label bold flex_column justify_center">Name</div>
        """
        return self.project_cards.nth(index).locator(".label").inner_text().strip()

    def open_project_by_index(self, index: int) -> str:
        """Capture the card's name label, visually highlight it and pause
        so it's identifiable in a headed run, click it to open the
        project, wait for the examples browser to close, and return the
        captured name.

        With up to ~90 cards on screen, "click the Nth one" is otherwise
        impossible for a human watching the browser to follow -- the
        highlight (a thick red outline) plus an explicit pause makes it
        visible which project is about to be opened, before the click
        happens.
        """
        card = self.project_cards.nth(index)
        card.scroll_into_view_if_needed()
        name = card.locator(".label").inner_text().strip()

        card.evaluate(
            "el => { el.style.outline = '6px solid red'; el.style.outlineOffset = '-3px'; }"
        )
        self.page.wait_for_timeout(1500)

        card.click()
        self.expect_not_visible()
        # Pause after the project has actually loaded, not just before the
        # click -- without this the test raced straight into the next
        # assertions the instant the examples screen closed, giving no
        # time to actually read the toolbar project name or see the
        # yellow workspace note before the test moved on.
        self.page.wait_for_timeout(2000)
        return name

    def get_yellow_note_project_name(self) -> str:
        """Extract the project name from the Blockly workspace comment that
        appears (as a yellow sticky note) after an example project opens.

        Handles all three per-product formats -- see the module docstring.

        Uses page.evaluate() against the main frame document -- confirmed
        reachable there even though the Blockly canvas is in a same-page
        SVG <foreignObject>.
        """
        value = self.page.evaluate(
            "() => { const t = document.querySelector('textarea.blocklyCommentTextarea');"
            " return t ? t.value : ''; }"
        )
        match = _NOTE_NAME_RE.search(value.replace("\r\n", "\n"))
        return match.group(1).strip() if match else ""

    def expect_yellow_note_with_project_name(self):
        """Assert the yellow workspace comment is present and has a populated
        project-name field after opening an example project."""
        name = self.get_yellow_note_project_name()
        assert name, (
            "Expected a yellow workspace comment starting 'Project: {name}' (or "
            "'Project Name: {name}') after opening an example, but the textarea "
            "was empty or missing that format."
        )
