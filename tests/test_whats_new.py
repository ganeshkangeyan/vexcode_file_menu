"""
Regression tests: File > What's New.

Confirmed test plan (live-verified against the real app, 2026-08-23):

  1. File > What's New opens a panel centered on screen (.whatsnew_window,
     inside a .vca_lightbox modal wrapper).
  2. The panel's title contains "What's New" -- the real full title is
     "VEXcode V5 - What's New", but per the confirmed scope we only assert
     the substring, not the dynamic changelog content below it.
  3. Clicking Close closes the panel.

Note: this is the exact same dialog the app can also auto-show on load
(gated by a v5version localStorage flag) -- see
BasePage.dismiss_whats_new_if_present(), which every test already relies on
via wait_until_loaded() to keep that auto-popup from blocking the first
real interaction. This test triggers it deliberately via the menu instead.
"""
import pytest

pytestmark = pytest.mark.whats_new


def test_whats_new_opens_with_title_and_closes(file_menu):
    dialog = file_menu.open_whats_new()

    dialog.expect_title_contains_whats_new()

    dialog.close()
