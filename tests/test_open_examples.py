"""
Regression tests: File > Open Examples (Blocks projects only).

All selectors confirmed against the live app (codev5.vex.com) on 2026-08-23
via direct Playwright DOM inspection -- see pages/open_examples_page.py for
the full confirmed-selector inventory.

Test case numbering matches the plan agreed with the user:

  19. File > Open Examples opens the examples browser, titled
      "Choose a Blocks example project".
  20. Back button returns to the editor; current project untouched.
  21. Re-opening after Back shows the same screen/title again.
  22. All 13 category tabs are visible in the filter bar.
  23. Switching to each non-All category shows at least one project.
  24. Returning to "All" restores the full 94-project list.
  25-27. First project: name captured from browser matches name in the
         yellow workspace comment after the project opens.
  28-30. Second project: same name-match flow, different card.

Unlike File > Open, this feature needs no mock -- Open Examples is a
fully in-page screen with no native OS dialogs involved.
"""
import pytest

from pages.open_examples_page import ALL_CATEGORY_TABS, EXPECTED_ALL_COUNT

pytestmark = pytest.mark.open_examples

NON_ALL_CATEGORIES = [t for t in ALL_CATEGORY_TABS if t != "All"]


# --- Navigation (tests 19-21) --------------------------------------------

def test_open_examples_shows_title(file_menu):
    """Test case 19: examples browser opens with the correct title."""
    file_menu.open_examples()


def test_open_examples_back_returns_to_editor_untouched(file_menu):
    """Test case 20: Back closes the browser; default Blocks project intact."""
    examples = file_menu.open_examples()
    examples.go_back()
    file_menu.expect_blocks_mode()


def test_reopening_open_examples_after_back_shows_same_screen(file_menu):
    """Test case 21: re-opening after Back shows the same title again."""
    examples = file_menu.open_examples()
    examples.go_back()
    examples_again = file_menu.open_examples()
    examples_again.expect_visible()


# --- Category tabs (tests 22-24) -----------------------------------------

def test_all_category_tabs_visible_and_clickable(file_menu):
    """Test case 22: all 13 category tabs are visible in the filter bar."""
    examples = file_menu.open_examples()
    examples.expect_all_category_tabs_present()


@pytest.mark.parametrize("category", NON_ALL_CATEGORIES)
def test_switching_category_updates_project_grid(file_menu, category):
    """Test case 23: switching to each category shows at least one project."""
    examples = file_menu.open_examples()
    examples.click_category(category)
    count = examples.visible_card_count()
    assert count > 0, (
        f"Expected at least one project card in category '{category}', "
        f"but the grid was empty after switching."
    )


def test_returning_to_all_shows_full_list(file_menu):
    """Test case 24: clicking All after a category restores the full 94-card list."""
    examples = file_menu.open_examples()
    examples.click_category("Motion")
    examples.click_category("All")
    count = examples.visible_card_count()
    assert count == EXPECTED_ALL_COUNT, (
        f"Expected {EXPECTED_ALL_COUNT} cards after returning to 'All', "
        f"got {count}."
    )


# --- Project name verification (tests 25-30) -----------------------------
#
# Tests 25-27 and 28-30 each form one continuous flow: capture the card
# name, open the project, confirm the yellow workspace comment appears,
# then compare the two names. They are combined into single test functions
# because the name captured in step 25 must be carried into step 27 --
# there is no way to split them across separate test functions without
# losing that value.

def test_first_project_name_matches_yellow_note(file_menu):
    """Test cases 25-27: first project in 'All'.

    25: the card label is readable and non-empty.
    26: opening the project closes the browser and shows the yellow note.
    27: the project name in the yellow note exactly matches the card label.
    """
    examples = file_menu.open_examples()

    # 25 -- capture name
    name_from_browser = examples.get_card_name(0)
    assert name_from_browser, (
        "Expected a non-empty project name label on the first card in 'All'"
    )

    # 26 -- open the project
    opened_name = examples.open_project_by_index(0)
    assert opened_name == name_from_browser, (
        "Card name changed between reading it and clicking it -- "
        f"captured: {name_from_browser!r}, got at click time: {opened_name!r}"
    )
    file_menu.expect_blocks_mode()
    examples.expect_yellow_note_with_project_name()

    # 27 -- compare names
    name_from_note = examples.get_yellow_note_project_name()
    assert name_from_note == name_from_browser, (
        f"Project name mismatch.\n"
        f"  Card label in examples browser : {name_from_browser!r}\n"
        f"  Name in yellow workspace note  : {name_from_note!r}"
    )


def test_second_project_name_matches_yellow_note(file_menu):
    """Test cases 28-30: second project in 'All' (index 1).

    28: the card label is readable and non-empty.
    29: opening the project closes the browser and shows the yellow note.
    30: the project name in the yellow note exactly matches the card label.
    """
    examples = file_menu.open_examples()

    # 28 -- capture name
    name_from_browser = examples.get_card_name(1)
    assert name_from_browser, (
        "Expected a non-empty project name label on the second card in 'All'"
    )

    # 29 -- open the project
    opened_name = examples.open_project_by_index(1)
    assert opened_name == name_from_browser, (
        "Card name changed between reading it and clicking it -- "
        f"captured: {name_from_browser!r}, got at click time: {opened_name!r}"
    )
    file_menu.expect_blocks_mode()
    examples.expect_yellow_note_with_project_name()

    # 30 -- compare names
    name_from_note = examples.get_yellow_note_project_name()
    assert name_from_note == name_from_browser, (
        f"Project name mismatch.\n"
        f"  Card label in examples browser : {name_from_browser!r}\n"
        f"  Name in yellow workspace note  : {name_from_note!r}"
    )
