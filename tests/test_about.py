"""
Regression tests: File > About.

Confirmed test plan (live-verified against the real app, 2026-08-23):

  1. File > About opens a panel centered on screen (.about_window).
  2. The panel contains two links: Privacy Policy and Acknowledgements.
     Both are bare <a> elements (no href attribute -- JS-driven, not plain
     navigation).
  3. Clicking Privacy Policy opens a real new browser tab to
     vexrobotics.com/software-privacy-policy.
  4. Clicking Acknowledgements does NOT open a new tab (confirmed with two
     separate live checks, including one waiting 10s in isolation) -- it
     opens an in-app credits panel (.credits_window) instead, listing
     open-source license/copyright entries.
  5. That credits panel's content genuinely overflows -- the inner .credits
     div has scrollHeight (~427000px, confirmed live) far exceeding its
     clientHeight (~480px), not just a visual clip.
  6. Clicking anywhere outside the credits panel closes it.
"""
import pytest

pytestmark = pytest.mark.about


def test_about_shows_both_links(file_menu):
    about = file_menu.open_about()
    about.expect_links_present()


def test_about_privacy_policy_opens_real_external_page(file_menu):
    about = file_menu.open_about()

    with file_menu.page.context.expect_page() as new_page_info:
        about.privacy_policy_link.click()
    new_page = new_page_info.value
    new_page.wait_for_load_state("load", timeout=10000)

    assert "vexrobotics.com" in new_page.url, (
        f"Expected Privacy Policy to open the real VEX Robotics site, got {new_page.url}"
    )
    assert "privacy-policy" in new_page.url
    new_page.close()


def test_about_acknowledgements_opens_scrollable_panel_and_closes_on_outside_click(file_menu):
    about = file_menu.open_about()

    credits = about.open_credits_panel()
    credits.expect_scrollable()

    credits.close_by_clicking_outside()
