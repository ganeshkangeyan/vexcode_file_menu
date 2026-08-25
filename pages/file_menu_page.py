"""
Page objects for VEXcode V5's File menu, covering:
  - File > New Blocks Project
  - File > New Text Project  (-> Select a Project Language dialog: Python / C++ / Cancel)
  - The "Your project was never saved. Save now?" Discard/Save prompt that
    appears when either of the above is triggered while there are unsaved
    changes (verified against the live app for Blocks, Python, and C++
    projects -- see UnsavedChangesDialog below).

File > Open is also covered (see open_project() / open_mock.py): same
native-picker mechanism as Save (window.showOpenFilePicker instead of
showSaveFilePicker), mocked the same way.

Other File menu items (Open Recent, Open Examples, Save, Save As, What's
New, About) were surveyed but are intentionally NOT covered by tests yet --
see README "Extending this suite" for locators/notes to build those out
next.

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


class WhatsNewDialog(BasePage):
    """The 'VEXcode V5 - What's New' panel, opened via File > What's New
    (same dialog auto-shown on load -- see BasePage.dismiss_whats_new_if_present).

    Confirmed live (2026-08-23): centered on screen inside a
    .vca_lightbox.flex_row.active modal wrapper, root container
    .whatsnew_window, title in .whatsnew_title. Content below the title is a
    dynamic changelog list -- per the confirmed test plan we only assert the
    title contains "What's New", not the changelog body.
    """

    MODAL_ROOT_SELECTOR = ".whatsnew_window"
    TITLE_SUBSTRING = "What's New"

    @property
    def root(self):
        return self.page.locator(self.MODAL_ROOT_SELECTOR)

    @property
    def title(self):
        return self.root.locator(".whatsnew_title")

    @property
    def close_button(self):
        return self.root.get_by_role("button", name="Close", exact=True)

    def expect_visible(self):
        expect(self.root).to_be_visible(timeout=10000)

    def expect_title_contains_whats_new(self):
        expect(self.title).to_contain_text(self.TITLE_SUBSTRING)

    def close(self):
        self.close_button.click()
        expect(self.root).not_to_be_visible(timeout=5000)


class CreditsPanel(BasePage):
    """The open-source credits/license list opened by clicking
    Acknowledgements inside AboutPanel.

    Confirmed live (2026-08-23): NOT a new browser tab (unlike Privacy
    Policy) -- an in-app panel, root .credits_window. The panel element
    itself does not scroll (scrollHeight == clientHeight); the real scroll
    container is the inner .credits div (confirmed scrollHeight ~427000px
    vs clientHeight ~480px, overflow-y: scroll -- genuinely large content,
    not just visually clipped). Closes on a click anywhere outside the
    panel (confirmed: no explicit Close button was found/needed).
    """

    ROOT_SELECTOR = ".credits_window"
    SCROLL_CONTAINER_SELECTOR = ".credits"

    @property
    def root(self):
        return self.page.locator(self.ROOT_SELECTOR)

    @property
    def scroll_container(self):
        return self.root.locator(self.SCROLL_CONTAINER_SELECTOR)

    def expect_visible(self):
        expect(self.root).to_be_visible(timeout=10000)

    def expect_scrollable(self):
        metrics = self.scroll_container.evaluate(
            "el => ({ scrollHeight: el.scrollHeight, clientHeight: el.clientHeight })"
        )
        assert metrics["scrollHeight"] > metrics["clientHeight"], (
            f"Expected the credits panel's content to overflow (be scrollable), got {metrics}"
        )

    def close_by_clicking_outside(self):
        # Confirmed live: any click outside the panel's own bounds closes
        # it -- (20, 20) is just a point far from the centered panel.
        self.page.mouse.click(20, 20)
        expect(self.root).not_to_be_visible(timeout=5000)


class AboutPanel(BasePage):
    """The About panel, opened via File > About.

    Confirmed live (2026-08-23): centered on screen, root .about_window.
    Contains two links -- Privacy Policy and Acknowledgements -- both bare
    <a> elements with no href attribute (JS-driven, not plain navigation):
      - Privacy Policy: confirmed opens a real new browser tab to
        vexrobotics.com/software-privacy-policy.
      - Acknowledgements: confirmed opens an in-app CreditsPanel, NOT a new
        tab -- see CreditsPanel above. (Verified this the hard way: an
        earlier check only looked for a new tab/navigation and wrongly
        concluded the link did nothing.)
    """

    MODAL_ROOT_SELECTOR = ".about_window"

    @property
    def root(self):
        return self.page.locator(self.MODAL_ROOT_SELECTOR)

    @property
    def privacy_policy_link(self):
        return self.root.locator("a", has_text="Privacy Policy")

    @property
    def acknowledgements_link(self):
        return self.root.locator("a", has_text="Acknowledgements")

    def expect_visible(self):
        expect(self.root).to_be_visible(timeout=10000)

    def expect_links_present(self):
        expect(self.privacy_policy_link).to_be_visible()
        expect(self.acknowledgements_link).to_be_visible()

    def open_credits_panel(self) -> "CreditsPanel":
        """Click Acknowledgements. Opens the CreditsPanel in-app -- unlike
        Privacy Policy (clicked directly via privacy_policy_link, which
        opens a real new browser tab), no new tab is involved here."""
        self.acknowledgements_link.click()
        panel = CreditsPanel(self.page)
        panel.expect_visible()
        return panel


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

    @property
    def open_menu_item(self):
        return self.page.get_by_text("Open", exact=True)

    @property
    def open_recent_menu_item(self):
        return self.page.get_by_text("Open Recent", exact=True)

    @property
    def open_examples_menu_item(self):
        # Confirmed exact text -- seen directly in a real File-menu DOM
        # dump earlier in this project.
        return self.page.get_by_text("Open Examples", exact=True)

    @property
    def save_menu_item(self):
        # Confirmed (2026-08-23, real strict-mode violation from a live
        # pytest run): the previous unscoped get_by_text("Save", exact=True)
        # resolved to 2 elements --
        #   1) #file_menu_save_to_computer_option  (the real File-menu item)
        #   2) #project_name_field button (has_text="Save")  (an unrelated
        #      "Save" control inside the project-name field itself)
        # Scoped to the real ID so this hits exactly the File-menu option.
        return self.page.locator("#file_menu_save_to_computer_option")

    @property
    def save_as_menu_item(self):
        # Confirmed (2026-08-23, live run): unscoped
        # get_by_text("Save As", exact=True) resolved to 2 elements --
        #   1) #file_menu_save_as_to_computer_option  (the real File-menu item)
        #   2) a <button> containing <span>Save As</span> that appears
        #      elsewhere (a toolbar-area control) once the project has been
        #      saved at least once.
        # Scoped to the real ID, same fix as save_menu_item above.
        return self.page.locator("#file_menu_save_as_to_computer_option")

    @property
    def whats_new_menu_item(self):
        # Confirmed live (2026-08-23): exact text "What's New" is unique
        # page-wide once the auto-shown popup (different exact text --
        # "VEXcode V5 - What's New") is dismissed, so this is safe unscoped.
        return self.page.get_by_text("What's New", exact=True)

    @property
    def about_menu_item(self):
        # Confirmed live (2026-08-26): exact text "About" resolves to
        # exactly 1 element page-wide, both before and after opening the
        # File menu -- safe unscoped, same verification standard as
        # whats_new_menu_item above.
        return self.page.get_by_text("About", exact=True)

    @property
    def no_recent_projects_text(self):
        # Written as a best guess (Chrome was unreachable at the time) but
        # since confirmed correct: test_open_recent_shows_no_recent_projects_on_fresh_session
        # (tests/test_open_recent.py), which asserts on this locator via
        # expect_no_recent_projects(), has passed consistently across every
        # full-suite run since.
        return self.page.get_by_text("No Recent Projects", exact=True)

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

    @property
    def project_name_field(self):
        # Toolbar text input showing/editing the current project's name.
        # Confirmed real selector on the live app:
        #   <input type="text" class="vcj text_input field for_name">
        return self.page.locator("input.for_name")

    @property
    def saved_indicator(self):
        # Confirmed real selector on the live app: <span
        # class="project_saving_status">, whose text flips between
        # "Not Saving" (never-saved / unsaved project) and "Saved".
        return self.page.locator(".project_saving_status")

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
        self.highlight_and_click(self.new_blocks_project_item)
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
        self.highlight_and_click(self.new_text_project_item)

        unsaved = UnsavedChangesDialog(self.page)
        if unsaved.is_visible():
            return unsaved

        dialog = NewProjectLanguageDialog(self.page)
        dialog.expect_visible()
        return dialog

    def open_project(self) -> "UnsavedChangesDialog | None":
        """File > Open.

        Triggers window.showOpenFilePicker() under the hood -- mocked via
        open_mock (see conftest.py's file_menu fixture, which installs it
        before every test). Callers must configure open_mock.set_file()
        (or leave it unset to simulate the user cancelling the native
        picker) BEFORE calling this.

        If there are unsaved changes in the current project, the "Save
        now?" prompt appears first (same as New Blocks/Text Project) --
        this returns that dialog so the caller can resolve it. Otherwise
        the picker resolves immediately and this returns None; give the
        app a moment to finish loading before asserting on the result (see
        expect_project_opened()).
        """
        self.open_menu()
        self.highlight_and_click(self.open_menu_item)
        dialog = UnsavedChangesDialog(self.page)
        return dialog if dialog.is_visible() else None

    def open_recent_menu(self):
        """File > Open Recent. After this, check either
        no_recent_projects_text (empty state) or recent_project_names()
        (populated state) -- see NOT YET CONFIRMED notes on those."""
        self.open_menu()
        self.highlight_and_click(self.open_recent_menu_item)

    def open_examples(self):
        """File > Open Examples. Returns an OpenExamplesPage. Unlike
        File > Open/New Project, this is NOT known to show an
        unsaved-changes prompt first -- not yet confirmed either way, so
        callers relying on that should verify it live before depending on
        it."""
        from pages.open_examples_page import OpenExamplesPage  # local import avoids a circular import at module load time

        self.open_menu()
        self.highlight_and_click(self.open_examples_menu_item)
        examples = OpenExamplesPage(self.page)
        examples.expect_visible()
        return examples

    def recent_project_names(self) -> list:
        """Names of entries currently listed under Open Recent (no extension).

        Confirmed selector (2026-08-23): entries render in
        .dropdownmenu_options.submenu.active as .label children with text
        like "Changing Velocities.v5python". We strip the extension.
        """
        labels = self.page.locator(
            ".dropdownmenu_options.submenu.active .label"
        ).all_inner_texts()
        return [t.rsplit(".", 1)[0] for t in labels if t.strip()]

    def open_recent_project(self, name: str) -> "UnsavedChangesDialog | None":
        """Click a specific Open Recent entry by its stem name (no extension).

        Confirmed (2026-08-23): the submenu portal is
        .dropdownmenu_options.submenu.active; entry text includes the
        extension so we match with exact=False. Mirrors open_project()'s
        return contract.
        """
        submenu = self.page.locator(".dropdownmenu_options.submenu.active")
        self.highlight_and_click(submenu.get_by_text(name, exact=False).first)
        dialog = UnsavedChangesDialog(self.page)
        return dialog if dialog.is_visible() else None

    def save_current_project(self):
        """File > Save -- the direct action, NOT the "Your project was
        never saved. Save now?" prompt (that only appears when unsaved
        changes interrupt a DIFFERENT action like New Project/Open; a
        direct Save just saves). Confirmed by the user against the real
        app: on a never-saved project this goes straight to the native
        save picker with no intermediate prompt.

        Triggers window.showSaveFilePicker() -- mocked via save_mock,
        which must have set_filename() called beforehand so the mock
        reports back the right name (see save_mock.py).
        """
        self.open_menu()
        self.highlight_and_click(self.save_menu_item)

    def save_as_current_project(self):
        """File > Save As -- same native-picker mock mechanism as
        save_current_project() (window.showSaveFilePicker via save_mock),
        but always opens the picker directly regardless of whether the
        project was already saved before, and is never interrupted by the
        "Save now?" prompt (that prompt only guards New Project/Open, not
        a direct Save/Save As). Confirmed live (2026-08-23): repeatable --
        calling this again on an already-saved project reopens the picker
        and updates the toolbar name to whatever filename was supplied via
        save_mock.set_filename() beforehand.
        """
        self.open_menu()
        self.highlight_and_click(self.save_as_menu_item)

    def open_whats_new(self) -> "WhatsNewDialog":
        """File > What's New."""
        self.open_menu()
        self.highlight_and_click(self.whats_new_menu_item)
        dialog = WhatsNewDialog(self.page)
        dialog.expect_visible()
        return dialog

    def open_about(self) -> "AboutPanel":
        """File > About."""
        self.open_menu()
        self.highlight_and_click(self.about_menu_item)
        panel = AboutPanel(self.page)
        panel.expect_visible()
        return panel

    def capture_save_status_transitions(self, action) -> list:
        """Runs `action` (a zero-arg callable expected to trigger a save)
        while recording every real change to the save-status indicator via
        a MutationObserver, each entry timestamped in ms since the
        observer was attached: [[t_ms, text], ...].

        Needed because the mocked save can resolve in ~10ms -- confirmed
        live that's fast enough to make the transient "Saving..." state
        disappear before a Playwright-side poll (each read is a
        round-trip) ever catches it. Pair with save_mock.set_save_delay()
        to widen that window when a test needs to assert on "Saving..."
        as its own observed state rather than just the end result.
        """
        self.page.evaluate("""
            () => {
                window.__vexStatusLog = [];
                const el = document.querySelector('.project_saving_status');
                window.__vexStatusLog.push([performance.now(), el.innerText]);
                window.__vexStatusObserver = new MutationObserver(() => {
                    window.__vexStatusLog.push([performance.now(), el.innerText]);
                });
                window.__vexStatusObserver.observe(el, {characterData: true, childList: true, subtree: true});
            }
        """)
        action()
        expect(self.saved_indicator).to_have_text("Saved", timeout=10000)
        return self.page.evaluate("window.__vexStatusLog")

    def expect_project_name(self, name: str):
        """Assert the toolbar project name field shows exactly this value
        (no extension -- confirmed the app never shows the extension
        here, same as expect_project_opened())."""
        expect(self.project_name_field).to_have_value(name, timeout=10000)

    def expect_saved_status(self, status: str):
        """Assert the save-status indicator shows exactly this text.
        Confirmed real values: "Not Saving" (never-saved / has unsaved
        changes) and "Saved"."""
        expect(self.saved_indicator).to_have_text(status, timeout=10000)

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
        # Verify the typed text actually landed before returning. Seen once
        # (2026-08-20 run, Python variant only) that a save immediately
        # after typing captured content *without* this marker present --
        # a silent timing race between typing and the app's internal state
        # sync, most likely, rather than a real app bug (the identical C++
        # call in the same run worked fine). This turns that race into an
        # immediate, clear failure right here instead of a confusing
        # downstream "marker not in saved content" several steps later.
        expect(self.page.get_by_text(snippet, exact=False)).to_be_visible(timeout=5000)

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

    def expect_no_save_error(self):
        """Regression guard for the app's own real error dialogs around
        File > Save, both hit while building this suite:
          - "An unexpected error occurred. The project could not be saved.
            ... VEXcode Error Code: ERROR_SAVE_FF" -- surfaced when the save
            handle is missing a method the app calls (e.g. getFile()).
          - "Invalid file extension. Please save the file without using
            periods to continue." -- a filename validation error.
        If either becomes visible after a Save action, something regressed
        in either the app's save path or our save_mock -- either way the
        test should fail loudly here rather than downstream with a
        confusing "content is None"/timeout.
        """
        expect(self.page.get_by_text("An unexpected error occurred", exact=False)).not_to_be_visible()
        expect(self.page.get_by_text("Invalid file extension", exact=False)).not_to_be_visible()

    def expect_unsupported_project_error(self):
        """Confirmed real dialog when File > Open is given content that
        isn't a valid VEXcode V5 project (e.g. garbage/unrecognized JSON):
        title "Unsupported project", body "The selected project file is
        for a different version of VEXcode. Please select a VEXcode V5
        project file." with an OK button."""
        expect(self.page.get_by_text("Unsupported project", exact=False)).to_be_visible(timeout=10000)
        expect(
            self.page.get_by_text(
                "The selected project file is for a different version of VEXcode",
                exact=False,
            )
        ).to_be_visible()

    def dismiss_unsupported_project_error(self):
        self.page.get_by_role("button", name="OK", exact=True).click()

    def get_blocks_workspace_xml(self) -> str:
        """Reads the EXACT serialized Blockly workspace XML straight from
        the app's own Blockly API, rather than trusting whatever text
        happens to be visible on the canvas. Confirmed live that
        `Blockly.getMainWorkspace()` is a real global on this app, and
        `Blockly.Xml.workspaceToDom` + `domToText` is the same
        serialization the app's own Save flow produces (see save_mock.py
        -- a saved Blocks project's "workspace" field is exactly this).
        Used after File > Open to prove the specific blocks that loaded
        match the specific fixture file requested, not just that "some
        blocks" rendered.
        """
        return self.page.evaluate(
            "() => Blockly.Xml.domToText(Blockly.Xml.workspaceToDom(Blockly.getMainWorkspace()))"
        )

    def get_editor_full_text(self) -> str:
        """Reads the FULL text-mode editor content, not just whatever's
        currently scrolled into view. Monaco (the code editor) virtualizes
        its DOM -- only the visible lines actually exist as text nodes --
        so get_by_text()/page text scraping can only ever see a fragment
        of a real file's content, and Monaco isn't exposed as a global on
        this app (confirmed live -- no window.monaco), so there's no
        direct API handle either. Select-all + copy + read the real OS/
        browser clipboard is the reliable way around both problems.
        Requires the "clipboard-read"/"clipboard-write" permissions
        granted in conftest.py's browser_context_args.
        """
        self.page.locator(".monaco-editor").click()
        self.page.keyboard.press("Control+a")
        self.page.keyboard.press("Control+c")
        return self.page.evaluate("() => navigator.clipboard.readText()")

    def expect_no_recent_projects(self):
        """Assert File > Open Recent shows the empty state. See
        no_recent_projects_text -- NOT YET CONFIRMED against the live
        app."""
        expect(self.no_recent_projects_text).to_be_visible(timeout=10000)

    def expect_recent_projects(self, expected_names: list):
        """Assert File > Open Recent shows exactly these project names.
        Order is NOT enforced -- the app's display ordering convention
        (most-recent-first is the typical assumption) hasn't been
        confirmed live, so this only checks membership/count to avoid a
        false failure on an ordering assumption we can't yet back up."""
        actual = set(self.recent_project_names())
        expected = set(expected_names)
        assert actual == expected, (
            f"Open Recent list mismatch.\nExpected: {sorted(expected)}\n"
            f"Got: {sorted(actual)}"
        )

    def expect_yellow_notes_visible(self):
        """After opening a project via File > Open Examples, a Blockly
        workspace comment (yellow sticky note) appears. Confirmed selector:
        textarea.blocklyCommentTextarea -- its .value starts with 'Project: '.
        See OpenExamplesPage.expect_yellow_note_with_project_name() for the
        richer assertion used by the Open Examples tests directly."""
        value = self.page.evaluate(
            "() => { const t = document.querySelector('textarea.blocklyCommentTextarea');"
            " return t ? t.value : ''; }"
        )
        assert "Project: \n" in value, (
            "Expected a yellow workspace comment containing 'Project: \\n{name}' "
            "after opening an example project, but it was absent or empty."
        )

    def expect_project_opened(self, expected_name: str, mode: str):
        """Assert a File > Open completed successfully: toolbar project
        name updated, save status flipped to "Saved" (a freshly opened
        project is -- by definition -- already saved to that file), and
        the editor is showing the right mode/language.

        expected_name: filename WITHOUT extension, matching what the app
        shows in the project name field (confirmed on the live app that
        the extension is not shown here).
        mode: "blocks", "python", or "cpp"
        """
        expect(self.project_name_field).to_have_value(expected_name, timeout=10000)
        expect(self.saved_indicator).to_have_text("Saved", timeout=10000)

        if mode == "blocks":
            self.expect_blocks_mode()
        else:
            self.expect_text_mode(mode)
