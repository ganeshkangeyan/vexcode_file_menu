"""
Shared pytest fixtures for the VEXcode V5 regression suite.

Run mode: headed Chromium by default (per team preference, so runs against
prod can be watched/debugged). Override with `pytest --headless` if you add
that flag later, or just flip `headless=True` below for CI.

Multi-site support: VEX's various web IDEs (VEXcode V5, and other products
built on the same component library -- same "vcj" class-prefixed buttons,
same modal structure, etc.) share this File menu design. Rather than forking
this suite per product, the *same* tests can run against any number of
sites via --sites / VEX_SITES -- see pytest_generate_tests() below. Nothing
in pages/ or tests/ is specific to codev5.vex.com; the only hardcoded URL in
this repo is the single-site default in pytest.ini, which --sites overrides.
"""
import base64
import os
import time

import pytest

from pages import open_mock, save_mock
from pages.file_menu_page import FileMenuPage


# --- Browser / context configuration -----------------------------------

@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, pytestconfig):
    # --slowmo is pytest-playwright's own built-in flag (default 0). We
    # raise that default to 500ms so a human watching the headed browser
    # can actually follow along, but an explicit --slowmo=N still wins.
    # Note: because pytest-playwright's default is 0 (not None), we can't
    # tell "user didn't pass --slowmo" apart from "user passed --slowmo=0"
    # -- if you genuinely want zero delay, use --slowmo=1.
    slow_mo = pytestconfig.getoption("--slowmo") or int(os.environ.get("VEX_SLOWMO", 500))
    return {
        **browser_type_launch_args,
        "headless": False,   # headed Chromium, per current test-plan scope
        "slow_mo": slow_mo,  # ms pause before every Playwright action -- see --slowmo
    }


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, browser_name):
    args = {
        **browser_context_args,
        "viewport": {"width": 1600, "height": 900},
    }
    # Confirmed live (2026-08-25): granting "clipboard-read"/"clipboard-write"
    # via context permissions is Chromium-only in Playwright -- Firefox
    # hard-errors the WHOLE context creation with "Unknown permission:
    # clipboard-read", which would otherwise break every single test on
    # Firefox, not just the clipboard-using ones. Edge runs on the Chromium
    # engine (launched via --browser=chromium --browser-channel=msedge), so
    # browser_name is still "chromium" there and this still applies.
    #
    # Needed (on Chromium) for FileMenuPage.get_editor_full_text() -- it
    # reads the Monaco editor's exact content via Ctrl+A/Ctrl+C + a real
    # navigator.clipboard.readText() call (Monaco virtualizes its DOM, so
    # only currently-scrolled-into-view lines exist as text nodes; this is
    # the only reliable way to get the FULL content back to verify File >
    # Open loaded the exact right file, not just a visible fragment of it).
    if browser_name == "chromium":
        args["permissions"] = ["clipboard-read", "clipboard-write"]
    return args


# --- CLI / env options ---------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--project-name",
        action="store",
        default=None,
        help="Base filename (without extension) to use when tests exercise "
             "File > Save. Falls back to VEX_PROJECT_NAME env var, then a "
             "timestamped default, so runs never collide on a hardcoded name.",
    )
    parser.addoption(
        "--sites",
        action="store",
        default=None,
        help="Comma-separated list of site base URLs to run the ENTIRE "
             "suite against, once per site -- e.g. "
             "'https://codev5.vex.com/,https://codeexp.vex.com/'. Falls "
             "back to the VEX_SITES env var. If neither is set, behaves "
             "exactly as before: a single run against --base-url (see "
             "pytest.ini). Use this when the same File menu test cases "
             "need to be verified across multiple VEX product sites that "
             "share this UI.",
    )


@pytest.fixture
def project_name(request) -> str:
    """Dynamic base filename for Save flows -- see save_mock.py.

    Priority: --project-name CLI flag > VEX_PROJECT_NAME env var > a
    timestamped default. Same value is reused across Blocks/Python/C++
    tests within a run; each test appends its own extension.
    """
    return (
        request.config.getoption("--project-name")
        or os.environ.get("VEX_PROJECT_NAME")
        or f"regression_{int(time.time())}"
    )


def _requested_sites(config) -> list:
    raw = config.getoption("--sites") or os.environ.get("VEX_SITES")
    if not raw:
        return []
    return [s.strip().rstrip("/") + "/" for s in raw.split(",") if s.strip()]


def pytest_generate_tests(metafunc):
    """When --sites / VEX_SITES lists more than one URL, parametrize the
    `base_url` fixture (the one pytest-playwright's `page` fixture reads
    to resolve page.goto("/")) across all of them, so every test that uses
    `file_menu` (and therefore `page` and therefore `base_url`) runs once
    per site automatically -- no test code changes needed. With zero or one
    site configured this is a no-op and --base-url behaves as always.
    """
    if "base_url" not in metafunc.fixturenames:
        return
    sites = _requested_sites(metafunc.config)
    if len(sites) > 1:
        metafunc.parametrize("base_url", sites)


# --- App-specific fixtures ------------------------------------------------

@pytest.fixture
def file_menu(page) -> FileMenuPage:
    """
    Installs the native Save- and Open-dialog mocks, navigates to the
    target site (whichever `base_url` resolved to -- see
    pytest_generate_tests above), and returns a FileMenuPage ready to use.
    Each test gets a fresh `page` (new browser context) from
    pytest-playwright, so there's no cross-test state leakage.
    """
    save_mock.install(page)  # must happen BEFORE goto -- see pages/save_mock.py
    open_mock.install(page)  # ditto -- see pages/open_mock.py
    page.goto("/")
    fmp = FileMenuPage(page)
    fmp.wait_until_loaded()
    return fmp


# --- Screenshot-on-failure for the pytest-html report ----------------------

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """On a failed test, grab a screenshot of whatever the browser was
    showing at the moment of failure and embed it directly in the
    pytest-html report (run with --html=report.html --self-contained-html).

    Only fires for the "call" phase (the actual test body, not setup/
    teardown) and only when the test failed -- a passing test gets no
    screenshot, keeping the report small. Reads the `page` fixture straight
    out of the failed test's own funcargs, so this works for every test
    using the `file_menu`/`page` fixtures without each test needing to do
    anything itself.
    """
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" or not report.failed:
        return

    page = item.funcargs.get("page")
    if page is None:
        return

    pytest_html = item.config.pluginmanager.getplugin("html")
    if pytest_html is None:
        return  # --html wasn't passed this run -- nothing to attach to

    try:
        screenshot_bytes = page.screenshot(full_page=True)
    except Exception:
        return  # page may already be closed/crashed -- don't mask the real failure

    screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
    extras = getattr(report, "extras", [])
    extras.append(pytest_html.extras.image(screenshot_b64, mime_type="image/png"))
    report.extras = extras
