"""
Capture real project files from a VEXcode site to use as test fixtures.

    python tools/capture_fixtures.py https://codeiq.vex.com/ [more sites...]

The File > Open / Open Recent tests need genuine project files for each
product -- every product only accepts its own extensions (.iqblocks,
.gopython, ...), so the V5 fixtures can't be reused. Rather than
hand-crafting JSON, this lets the app produce them itself:

  * Blocks: opens built-in examples (File > Open Examples) and saves each
    one with File > Save As.
  * Python / C++ (where the product has them): starts a new text project,
    adds a unique comment line, and saves it.

Saves go through the suite's own save mock (pages/save_mock.py), so nothing
is written to the site or to disk by the app -- the mock captures the bytes
the app would have written, and this script stores them in
tests/fixtures/<site key>/ together with a manifest.json that sites.py
reads to know which file is which.

Runs headed: Cloudflare blocks headless Chrome on these sites (see README).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from pages import open_mock, save_mock  # noqa: E402
from pages.file_menu_page import FileMenuPage  # noqa: E402
from sites import site_for_url  # noqa: E402

RECENT_NEEDED = 6  # Open Recent "keep last 5" test needs 6 distinct files
TEXT_NAMES = {"python": "Text Project Python", "cpp": "Text Project Cpp"}
TEXT_COMMENTS = {"python": "# fixture captured by tools/capture_fixtures.py",
                 "cpp": "// fixture captured by tools/capture_fixtures.py"}


def _new_page(browser, site, url):
    ctx = browser.new_context(viewport={"width": 1600, "height": 900},
                              permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    save_mock.install(page)
    open_mock.install(page)
    page.goto(url, timeout=60000)
    fm = FileMenuPage(page, site)
    fm.wait_until_loaded()
    return ctx, fm


def _save_as(fm, filename) -> str:
    save_mock.set_filename(fm.page, filename)
    fm.save_as_current_project()
    fm.expect_no_save_error()
    fm.expect_saved_status("Saved")
    saved = save_mock.get_saved_files(fm.page)
    content = saved[-1]["content"]
    assert content and json.loads(content), f"Nothing captured for {filename}"
    return content


def capture(url: str):
    site = site_for_url(url)
    out_dir = site.fixtures_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    written = {}  # mode or "blocksN" -> filename

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        # Example names first, so each example can be opened in a clean page.
        ctx, fm = _new_page(browser, site, url)
        examples = fm.open_examples()
        count = examples.visible_card_count()
        names = [examples.get_card_name(i) for i in range(count)]
        ctx.close()
        # The app rejects filenames containing periods ("Invalid file
        # extension"), so skip any example whose name has one.
        # Blocks files make up whatever the text files don't (6 on a
        # blocks-only product like 123), with at least 4 everywhere.
        blocks_wanted = max(4, RECENT_NEEDED - len(site.text_languages))
        picks = [i for i, n in enumerate(names) if n and "." not in n][:blocks_wanted]

        for n, index in enumerate(picks):
            ctx, fm = _new_page(browser, site, url)
            name = fm.open_examples().open_project_by_index(index)
            filename = name + site.extensions["blocks"]
            (out_dir / filename).write_text(_save_as(fm, name), encoding="utf-8")
            written[f"blocks{n}"] = filename
            print(f"  blocks  -> {filename}")
            ctx.close()

        for lang in site.text_languages:
            ctx, fm = _new_page(browser, site, url)
            fm.start_text_project(lang)
            fm.add_unsaved_text_change(TEXT_COMMENTS[lang])
            filename = TEXT_NAMES[lang] + site.extensions[lang]
            (out_dir / filename).write_text(_save_as(fm, TEXT_NAMES[lang]), encoding="utf-8")
            written[lang] = filename
            print(f"  {lang:7} -> {filename}")
            ctx.close()

        browser.close()

    blocks = [written[k] for k in sorted(written) if k.startswith("blocks")]
    texts = [written[lang] for lang in site.text_languages]
    open_fixtures = {"blocks": blocks[0], **{lang: written[lang] for lang in site.text_languages}}
    # Same shape as V5's list: a blocks file, then the text files, then
    # more blocks files -- 6 in total, oldest first.
    recent = ([blocks[0]] + texts + blocks[1:])[:RECENT_NEEDED]
    if len(recent) < RECENT_NEEDED:
        raise SystemExit(f"Only captured {len(recent)} files for {site.product}; need {RECENT_NEEDED}")

    manifest = {"site": url, "open": open_fixtures, "recent": recent}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"  manifest -> {out_dir / 'manifest.json'}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for site_url in sys.argv[1:]:
        print(site_url)
        capture(site_url)
