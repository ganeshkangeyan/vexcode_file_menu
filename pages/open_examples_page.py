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
  - Project cards: div.sample_file_btn  (94 total in the "All" view)
  - Card name:     div.label inside each card (plain text, no extension)
  - Yellow note:   textarea.blocklyCommentTextarea -- its .value (not
                   .innerText, which is always empty) contains:
                       "Project: \\n{name}\\n\\nDescription: \\n...\\n\\nConfiguration:\\n..."
                   The textarea lives in the main document via a Blockly
                   SVG <foreignObject> -- confirmed reachable via
                   page.evaluate() in the main frame context.
"""
import re

from playwright.sync_api import Page, expect

from pages.base_page import BasePage


ALL_CATEGORY_TABS = [
    "All", "Templates", "Motion", "Drivetrain", "Looks",
    "Magnet", "Arm", "Events", "Control", "Sensing",
    "Operators", "Variables", "My Blocks",
]

EXPECTED_ALL_COUNT = 94


class OpenExamplesPage(BasePage):
    BLOCKS_TITLE_TEXT = "Choose a Blocks example project"

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
        """Assert every known category tab is visible in the filter bar."""
        for name in ALL_CATEGORY_TABS:
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
        return self.project_cards.count()

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

        With up to 94 cards on screen, "click the Nth one" is otherwise
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

        Confirmed textarea value format:
            'Project: \\n{name}\\n\\nDescription: \\n...\\n\\nConfiguration:\\n...'

        Uses page.evaluate() against the main frame document -- confirmed
        reachable there even though the Blockly canvas is in a same-page
        SVG <foreignObject>.
        """
        value = self.page.evaluate(
            "() => { const t = document.querySelector('textarea.blocklyCommentTextarea');"
            " return t ? t.value : ''; }"
        )
        if "Project: \n" not in value:
            return ""
        return value.split("Project: \n")[1].split("\n\n")[0].strip()

    def expect_yellow_note_with_project_name(self):
        """Assert the yellow workspace comment is present and has a populated
        project-name field after opening an example project."""
        name = self.get_yellow_note_project_name()
        assert name, (
            "Expected a yellow workspace comment with 'Project: \\n{name}' after "
            "opening an example, but the textarea was empty or missing that format."
        )
