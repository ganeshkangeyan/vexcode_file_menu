"""
CI runner: run the suite against one or more VEXcode sites, one site at a
time, with one HTML + JUnit report per site. Used by the Jenkinsfile, and
works the same from a terminal:

    python tools/run_ci.py                                  # all 5 production sites
    python tools/run_ci.py --sites=v5,iq --markers="save or save_as"
    python tools/run_ci.py --sites=v5 --test-url=https://codev5-staging.vex.com/
    python tools/run_ci.py --browser=msedge

Every option falls back to an environment variable of the same name as the
Jenkins build parameter (SITES, TEST_URL, BROWSER, MARKERS), so Jenkins
never has to quote a marker expression for both sh and bat.

Sites run one after another, not in parallel: these are heavy apps behind
Cloudflare, and parallel headed runs on one machine caused page-load
timeouts (see README).

Output in reports/:  <key>.html (screenshots of failures embedded),
<key>.xml (JUnit -- test names prefixed with the site key so Jenkins shows
v5 and iq results separately), <key>.log (full pytest output).

Exit code: 0 all passed, 1 some tests failed, 2 a run couldn't happen at
all (bad option, nothing collected, pytest crashed) -- so Jenkins can mark
test failures UNSTABLE and setup problems FAILED.
"""
import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sites import SITES, site_by_name  # noqa: E402

BROWSERS = {
    "chromium": ["--browser=chromium"],
    "msedge": ["--browser=chromium", "--browser-channel=msedge"],
}


def _prefix_junit_names(xml_path: Path, key: str):
    """tests.test_open.test_x -> v5.tests.test_open.test_x, so the same test
    run on several sites doesn't collapse into one row in Jenkins."""
    if not xml_path.exists():
        return
    tree = ET.parse(xml_path)
    for case in tree.iter("testcase"):
        case.set("classname", f"{key}.{case.get('classname', '')}")
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)


def run_site(key: str, url: str, override: bool, browser: str, markers: str, reports: Path) -> int:
    cmd = [
        sys.executable, "-m", "pytest",
        f"--base-url={url}",
        *BROWSERS[browser],
        "-p", "no:cacheprovider",
        "-rfEs",
        f"--html={reports / (key + '.html')}", "--self-contained-html",
        f"--junitxml={reports / (key + '.xml')}",
        "-o", f"junit_suite_name={key}",
    ]
    if override:
        cmd.append(f"--site={key}")
    if markers:
        cmd += ["-m", markers]

    env = {**os.environ}
    env.setdefault("VEX_SLOWMO", "1")  # no human watching -- don't slow down

    print(f"\n=== {key}: {url}  ({browser}{', -m ' + repr(markers) if markers else ''})", flush=True)
    log_path = reports / f"{key}.log"
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            sys.stdout.write(line)
            log.write(line)
        proc.wait()
    _prefix_junit_names(reports / f"{key}.xml", key)
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sites", default=os.environ.get("SITES") or "all",
                    help="'all' or comma list of v5,123,go,exp,iq (env SITES)")
    ap.add_argument("--test-url", default=os.environ.get("TEST_URL", ""),
                    help="test build URL to run instead of production; needs exactly one site (env TEST_URL)")
    ap.add_argument("--browser", default=os.environ.get("BROWSER") or "chromium", choices=list(BROWSERS),
                    help="chromium or msedge (env BROWSER)")
    ap.add_argument("--markers", default=os.environ.get("MARKERS", ""),
                    help="pytest -m expression, e.g. 'save or save_as'; empty = everything (env MARKERS)")
    ap.add_argument("--reports", default=str(ROOT / "reports"))
    args = ap.parse_args()

    raw = args.sites.strip().lower()
    try:
        keys = ([cfg.key for cfg in SITES.values()] if raw in ("", "all")
                else [site_by_name(k).key for k in raw.split(",") if k.strip()])
    except KeyError as e:
        print(f"ERROR: {e}")
        return 2
    test_url = args.test_url.strip()
    if test_url and len(keys) != 1:
        print("ERROR: TEST_URL is one build of one product -- set SITES to that product "
              f"(one of {', '.join(c.key for c in SITES.values())}), not {args.sites!r}.")
        return 2

    reports = Path(args.reports)
    reports.mkdir(parents=True, exist_ok=True)
    for old in list(reports.glob("*.xml")) + list(reports.glob("*.html")) + list(reports.glob("*.log")):
        old.unlink()  # a stale report from an earlier build must not look like this build's result

    host_for = {cfg.key: host for host, cfg in SITES.items()}
    results = {}
    for key in keys:
        url = test_url or f"https://{host_for[key]}/"
        results[key] = run_site(key, url, bool(test_url), args.browser, args.markers.strip(), reports)

    print("\n=== Summary")
    meaning = {0: "passed", 1: "TESTS FAILED", 5: "NO TESTS MATCHED"}
    for key, rc in results.items():
        tail = (reports / f"{key}.log").read_text(encoding="utf-8").strip().splitlines()
        print(f"  {key:4} {meaning.get(rc, f'ERROR (pytest exit {rc})'):18} {tail[-1] if tail else ''}")

    codes = set(results.values())
    if codes <= {0}:
        return 0
    if codes <= {0, 1}:
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
