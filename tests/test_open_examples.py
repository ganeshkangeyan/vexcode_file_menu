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
  22. All category tabs are visible in the filter bar.
  23. Switching to each non-All category shows at least one project.
  24. Returning to "All" restores the full project list.

The tab names and the full-list count differ per product (V5: 13 tabs /
94 projects, 123: 11 / 17, GO: 12 / 26, EXP: 14 / 80, IQ: 12 / 75) and come
from the site settings in sites.py.
  25-27. First project: name captured from browser matches name in the
         yellow workspace comment after the project opens.
  28-30. Second project: same name-match flow, different card.

Unlike File > Open, this feature needs no mock -- Open Examples is a
fully in-page screen with no native OS dialogs involved.
"""
import pytest

from sites import SITES

pytestmark = pytest.mark.open_examples

# Category tabs are per product, but tests are collected once for all sites
# in the run (--sites can mix products) -- so parametrize over every tab
# name any product has, and skip the ones the site under test doesn't.
ALL_KNOWN_CATEGORIES = list(dict.fromkeys(
    t for s in SITES.values() for t in s.example_categories if t != "All"
))


def _non_all_categories(site):
    return [t for t in site.example_categories if t != "All"]


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
    """Test case 22: every category tab this product has is visible in the filter bar."""
    examples = file_menu.open_examples()
    examples.expect_all_category_tabs_present()


@pytest.mark.parametrize("category", [
    pytest.param(c, marks=pytest.mark.requires(f"examples_tab:{c}")) for c in ALL_KNOWN_CATEGORIES
])
def test_switching_category_updates_project_grid(file_menu, category):
    """Test case 23: switching to each category shows at least one project."""
    examples = file_menu.open_examples()
    examples.click_category(category)
    count = examples.visible_card_count()
    assert count > 0, (
        f"Expected at least one project card in category '{category}', "
        f"but the grid was empty after switching."
    )


def test_returning_to_all_shows_full_list(file_menu, site):
    """Test case 24: clicking All after a category restores the full list."""
    examples = file_menu.open_examples()
    examples.click_category(_non_all_categories(site)[0])
    examples.click_category("All")
    count = examples.visible_card_count()
    assert count == site.example_count, (
        f"Expected {site.example_count} cards after returning to 'All', "
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
    """Test cases 25-27: first example project in 'All' (Templates skipped
    -- they're blank worksheets whose note has no project name, see
    OpenExamplesPage.index_of_nth_project).

    25: the card label is readable and non-empty.
    26: opening the project closes the browser and shows the yellow note.
    27: the project name in the yellow note exactly matches the card label.
    """
    examples = file_menu.open_examples()
    index = examples.index_of_nth_project(0)

    # 25 -- capture name
    name_from_browser = examples.get_card_name(index)
    assert name_from_browser, (
        "Expected a non-empty project name label on the first project card in 'All'"
    )

    # 26 -- open the project
    opened_name = examples.open_project_by_index(index)
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
    """Test cases 28-30: second example project in 'All' (Templates
    skipped, same as the first-project test).

    28: the card label is readable and non-empty.
    29: opening the project closes the browser and shows the yellow note.
    30: the project name in the yellow note exactly matches the card label.
    """
    examples = file_menu.open_examples()
    index = examples.index_of_nth_project(1)

    # 28 -- capture name
    name_from_browser = examples.get_card_name(index)
    assert name_from_browser, (
        "Expected a non-empty project name label on the second project card in 'All'"
    )

    # 29 -- open the project
    opened_name = examples.open_project_by_index(index)
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
