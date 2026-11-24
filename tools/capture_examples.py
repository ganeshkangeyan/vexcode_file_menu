"""
Record the Open Examples catalog (every tab, every example name) of a
VEXcode site as the baseline that test builds are compared against.

    python tools/capture_examples.py https://codev5.vex.com/ [more sites...]
    python tools/capture_examples.py https://codev5-staging.vex.com/ --site=v5

Writes tests/fixtures/<site key>/examples.json:

    {"site": "https://codev5.vex.com/", "captured": "2026-11-25",
     "tabs": {"All": ["Accurate Turns", ...], "Templates": [...], ...}}

tests/test_examples_baseline.py then opens File > Open Examples on whatever
build the suite runs against and reports every tab or example that was
added or removed compared to this file.

Capture from PRODUCTION, and re-run it after each release goes live so the
baseline follows what customers have. Read-only: it only opens the
examples browser and reads the cards -- nothing is saved anywhere.

Runs headed: Cloudflare blocks headless Chrome on these sites (see README).
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from pages.file_menu_page import FileMenuPage  # noqa: E402
from sites import site_for_url  # noqa: E402


def capture(url: str, site_override=None):
    site = site_for_url(url, site_override)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(viewport={"width": 1600, "height": 900})
        page = ctx.new_page()
        page.goto(url, timeout=60000)
        fm = FileMenuPage(page, site)
        fm.wait_until_loaded()
        tabs = fm.open_examples().catalog()
        browser.close()

    baseline = {
        "site": url,
        "captured": datetime.date.today().isoformat(),
        "tabs": tabs,
    }
    out = site.examples_baseline_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for tab, names in tabs.items():
        print(f"  {tab:12} {len(names):3} examples")
    print(f"  -> {out}")

    # sites.py keeps its own tab list / "All" count for the other Open
    # Examples tests -- flag it if production has moved on from those.
    if tuple(tabs) != site.example_categories:
        print(f"  NOTE: tabs differ from example_categories in sites.py: {list(tabs)}")
    if len(tabs.get("All", [])) != site.example_count:
        print(f"  NOTE: 'All' has {len(tabs.get('All', []))} examples; "
              f"sites.py example_count is {site.example_count}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--site", help="product key (v5/123/go/exp/iq) when the URL doesn't show it")
    args = ap.parse_args()
    for site_url in args.urls:
        print(site_url)
        capture(site_url, args.site)
