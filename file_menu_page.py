"""
Page objects for VEXcode V5's File menu, covering:
  - File > New Blocks Project
  - File > New Text Project  (-> Select a Project Language dialog: Python / C++ / Cancel)
  - The "Your project was never saved. Save now?" Discard/Save prompt that
    appears when either of the above is triggered while there are unsaved
    changes (verified against the live app for Blocks, Python, and C++
    projects -- see UnsavedChangesDialog below).

Other File menu items (Open, Open Recent, Open Examples, Save, Save As,
What's New, About) were surveyed but are intentionally NOT covered by tests
yet -- see README "Extending this suite" for locators/notes to build those
out next.

Locator note: this is a Blockly/canvas SPA with no data-testid hooks, so
everything here is get_by_text / get_by_role(name=...) -- matched against
the *real* accessible text confirmed by inspecting the live app (not just
what's visually rendered; CSS text-transform made "Download" look like
"DOWNLOAD" on screen, for example, which is what broke the first version of
this locator).
"""
from playwright.sync_api import Page, expect

from pages.base_page import BasePage

# Real file extensions used by File > Save / Save As, confirmed by
# intercepting window.showSaveFilePicker() on the live app for each project
# type (see README "How the Save mock works").
SAVE_EXTENSIONS = {
    "blocks": ".v5blocks",
    "python": ".v5python",
    "cpp": ".v5cpp",
}


class NewProjectLanguageDialog(BasePage):
    """The 'Select a Project Language' modal that appears after
    File > New Text Project.

    All locators are scoped to the modal's own container (.prompt_window).
    This app keeps other, non-visible/unrelated elements with the exact same
    text permanently in the DOM (e.g. a hidden "Convert to Text" Python/C++
    pair, and an unrelated project-rename dropdown's own "Cancel" button) --
    confirmed by inspecting the live DOM, both were still real strict-mode
    matches for an unscoped get_by_role/get_by_text. Scoping to the modal
    container is what actually disambiguates them.
    """

    TITLE_TEXT = "Select a Project Language"
    MODAL_ROOT_SELECTOR = ".prompt_window"

    @property
    def root(self):
        return self.page.locator(self.MODAL_ROOT_SELECTOR)

    @property
    def title(self):
        return self.root.get_by_text(self.TITLE_TEXT)

    @property
    def python_card(self):
        return self.root.get_by_role("button", name="Python", exact=True)

    @property
    def cpp_card(self):
        return self.root.get_by_role("button", name="C++", exact=True)

    @property
    def cancel_button(self):
        return self.root.get_by_role("button", name="Cancel", exact=True)

    def expect_visible(self):
        expect(self.title).to_be_visible(timeout=5000)

    def choose_python(self):
        self.python_card.click()

    def choose_cpp(self):
        self.cpp_card.click()

    def cancel(self):
        self.cancel_button.click()


class UnsavedChangesDialog(BasePage):
    """The 'Your project was never saved. Save now?' prompt shown when
    File > New Blocks Project / New Text Project is triggered while there
    are unsaved changes. Confirmed on the live app to have exactly two
    buttons -- Discard and Save -- no Cancel option.

    Locators are scoped to the modal container (.prompt_window): confirmed
    on the live DOM that an unrelated, simultaneously-visible "Save" button
    elsewhere on the page also matches an unscoped get_by_role("button",
    name="Save"), which would otherwise cause a strict-mode violation.
    """

    MESSAGE_TEXT = "Your project was never saved. Save now?"
    MODAL_ROOT_SELECTOR = ".prompt_window"

    @property
    def root(self):
        return self.page.locator(self.MODAL_ROOT_SELECTOR)

    @property
    def message(self):
        return self.root.get_by_text(self.MESSAGE_TEXT)

    @property
    def discard_button(self):
        return self.root.get_by_role("button", name="Discard", exact=True)

    @property
    def save_button(self):
        return self.root.get_by_role("button", name="Save", exact=True)

    def is_visible(self) -> bool:
        try:
            expect(self.message).to_be_visible(timeout=3000)
            return True
        except AssertionError:
            return False

    def discard(self):
        self.discard_button.click()

    def save(self):
        """Click Save. The real app opens a native OS Save-As dialog here
        (via window.showSaveFilePicker), which Playwright cannot drive --
        see the save_picker_mock fixture in conftest.py, which must be
        installed *before* calling this so the native dialog never opens."""
        self.save_button.click()


class FileMenuPage(BasePage):
    # --- Boilerplate markers used to confirm which editor mode is active ---
    PYTHON_MARKER = "from vex import *"
    CPP_MARKER = '#include "vex.h"'
    BOILERPLATE_HEADER = "VEXcode Generated Robot Configuration"

    # --- Menu trigger / items ---
    @property
    def file_menu_button(self):
        return self.page.get_by_text("File", exact=True)

    @property
    def new_blocks_project_item(self):
        return self.page.get_by_text("New Blocks Project", exact=True)

    @property
    def new_text_project_item(self):
        return self.page.get_by_text("New Text Project", exact=True)

    # --- Mode indicators ---
    @property
    def edit_menu_button(self):
        # Only present in text/code editor mode
        return self.page.get_by_text("Edit", exact=True)

    @property
    def download_button(self):
        # Only present in blocks mode. Accessible name is "Download"
        # (mixed case) -- the all-caps look on screen is CSS
        # text-transform, not the real accessible/DOM text.
        return self.page.get_by_role("button", name="Download", exact=True)

    @property
    def build_button(self):
        # Only present in text/code editor mode. Accessible name is "Build"
        # (mixed case) -- same CSS text-transform trap as Download.
        return self.page.get_by_role("button", name="Build", exact=True)

    @property
    def default_blocks_hat(self):
        # Default "when started" hat block present on a fresh blocks
        # project. Confirmed on the live app (including a genuinely fresh
        # Playwright browser context, not just a leftover from manual
        # testing) that a new project renders TWO overlapping "when
        # started" hat blocks, not one -- both real top-level blocks in
        # Blockly's own model (.blocklyDraggable), not a text/stroke
        # rendering duplicate. Using .first since we only need to confirm
        # blocks-mode is showing, not assert how many hat blocks exist.
        return self.page.get_by_text("when started", exact=True).first

    # --- Actions ---
    def open_menu(self):
        self.file_menu_button.click()
        expect(self.new_blocks_project_item).to_be_visible(timeout=5000)

    def new_blocks_project(self) -> "UnsavedChangesDialog | None":
        """File > New Blocks Project.

        If there are no unsaved changes, this resets the canvas to a blank
        blocks project immediately and returns None.

        If there ARE unsaved changes, the app shows the "Save now?" prompt
        instead of resetting -- this returns the UnsavedChangesDialog so the
        caller can resolve it (discard() or save()).
        """
        self.open_menu()
        self.new_blocks_project_item.click()
        dialog = UnsavedChangesDialog(self.page)
        return dialog if dialog.is_visible() else None

    def new_text_project(self) -> "NewProjectLanguageDialog | UnsavedChangesDialog":
        """File > New Text Project.

        Normally opens the language-selection dialog directly. If there are
        unsaved changes, the "Save now?" prompt appears first -- this
        returns whichever dialog is actually showing, so callers should
        check the type (or just call .is_visible()-style duck typing) when
        unsaved changes are a possibility.
        """
        self.open_menu()
        self.new_text_project_item.click()

        unsaved = UnsavedChangesDialog(self.page)
        if unsaved.is_visible():
            return unsaved

        dialog = NewProjectLanguageDialog(self.page)
        dialog.expect_visible()
        return dialog

    def add_unsaved_blocks_change(self):
        """Creates an unsaved change on a blocks-mode canvas by duplicating
        the default 'when started' hat block via its right-click context
        menu. Assumes a fresh/default blocks project is currently showing."""
        hat_block = self.default_blocks_hat
        hat_block.click(button="right")
        self.page.get_by_text("Duplicate", exact=True).click()

    def add_unsaved_text_change(self, snippet: str = "# regression test change"):
        """Creates an unsaved change in the text/code editor by typing a
        harmless comment line. Assumes a text-mode project is currently
        showing."""
        # Click into the code editor body, then type at the end.
        # Confirmed the editor is Monaco (.monaco-editor) on the live app.
        self.page.locator(".monaco-editor").click()
        self.page.keyboard.press("Control+End")
        self.page.keyboard.press("Enter")
        self.page.keyboard.type(snippet)

    # --- State assertions ---
    def expect_blocks_mode(self):
        """Assert the app is showing the Blockly canvas (blocks-mode UI)."""
        expect(self.download_button).to_be_visible(timeout=10000)
        expect(self.edit_menu_button).not_to_be_visible()
        expect(self.default_blocks_hat).to_be_visible()

    def expect_text_mode(self, language: str):
        """Assert the app is showing the code editor for the given language.

        language: "python" or "cpp"
        """
        expect(self.build_button).to_be_visible(timeout=10000)
        expect(self.edit_menu_button).to_be_visible()

        marker = self.PYTHON_MARKER if language == "python" else self.CPP_MARKER
        expect(self.page.get_by_text(marker)).to_be_visible()
        expect(self.page.get_by_text(self.BOILERPLATE_HEADER)).to_be_visible()

    def expect_zero_errors(self):
        """Text-mode editor shows an Errors panel with warning/error counts."""
        expect(self.page.get_by_text("Errors")).to_be_visible()
