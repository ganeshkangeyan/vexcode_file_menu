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
from sites import SiteConfig, site_for_url


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
    # Headed by default; VEX_HEADLESS=1 runs headless (e.g. Jenkins/CI).
    headless = os.environ.get("VEX_HEADLESS", "0").lower() in ("1", "true", "yes")
    return {
        **browser_type_launch_args,
        "headless": headless,
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
    parser.addoption(
        "--site",
        action="store",
        default=None,
        help="Which VEXcode product the site under test is: v5, 123, go, exp "
             "or iq. Falls back to the VEX_SITE env var. Only needed for a "
             "test build whose URL doesn't show it (e.g. "
             "codev5-staging.vex.com, an IP, a preview host) -- production "
             "hosts and their subdomains (staging.codev5.vex.com) are "
             "recognised automatically.",
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
def site(base_url, pytestconfig) -> SiteConfig:
    """The per-site settings (extensions, languages, examples, fixtures)
    for whichever site this test is running against -- see sites.py.
    --site / VEX_SITE overrides the product for a test-build URL."""
    override = pytestconfig.getoption("--site") or os.environ.get("VEX_SITE")
    return site_for_url(base_url, override)


def _site_has(site: SiteConfig, feature: str) -> bool:
    if feature == "language_dialog":
        return site.language_dialog
    if feature == "text":
        return bool(site.text_languages)
    if feature.startswith("examples_tab:"):
        return feature.split(":", 1)[1] in site.example_categories
    return site.supports(feature)  # "blocks" / "python" / "cpp"


@pytest.fixture(autouse=True)
def _skip_unsupported_features(request):
    """`@pytest.mark.requires("cpp")` etc. skips a test on sites that don't
    have that feature (e.g. C++ on VEXcode GO, any text project on 123),
    so the report shows "skipped -- not on this product" instead of a
    misleading failure."""
    markers = list(request.node.iter_markers("requires"))
    if not markers or "base_url" not in request.fixturenames:
        return
    site = request.getfixturevalue("site")
    for m in markers:
        for feature in m.args:
            if not _site_has(site, feature):
                pytest.skip(f"{site.product} has no {feature!r}")


@pytest.fixture
def file_menu(page, site) -> FileMenuPage:
    """
    Installs the native Save- and Open-dialog mocks, navigates to the
    target site (whichever `base_url` resolved to -- see
    pytest_generate_tests above), and returns a FileMenuPage ready to use.
    Each test gets a fresh `page` (new browser context) from
    pytest-playwright, so there's no cross-test state leakage.
    """
    save_mock.install(page)  # must happen BEFORE goto -- see pages/save_mock.py
    open_mock.install(page)  # ditto -- see pages/open_mock.py
    # 60s, not Playwright's default 30s: these are heavy apps, and a busy
    # machine (several sites in parallel) regularly needed more than 30s
    # just to load -- confirmed 2026-10-24.
    page.goto("/", timeout=60000)
    fmp = FileMenuPage(page, site)
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
