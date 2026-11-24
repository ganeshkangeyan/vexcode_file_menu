"""
Regression test: the Open Examples catalog of the build under test matches
the production baseline.

The other Open Examples tests only check the tab list and the total number
of examples, so swapping one example for another goes unnoticed. This test
compares every example name in every tab against
tests/fixtures/<site>/examples.json -- recorded from production by
tools/capture_examples.py -- and lists exactly what was added or removed.

Typical use: point the suite at a test build (--base-url, plus --site if
the URL doesn't show the product) before a release. A failure here means
the test build's examples differ from what's live now. That can be
intended (new examples for the release) -- check the list in the failure
message, and once the release is live, re-capture the baseline from
production.

Order on screen is ignored; only which examples exist (and how many times)
counts.
"""
import json
from collections import Counter

import pytest

pytestmark = pytest.mark.open_examples


def _diff(expected: list, actual: list):
    missing = sorted((Counter(expected) - Counter(actual)).elements())
    added = sorted((Counter(actual) - Counter(expected)).elements())
    return missing, added


def test_examples_match_production_baseline(file_menu, site):
    path = site.examples_baseline_path
    if not path.exists():
        pytest.skip(f"No examples baseline for {site.product} -- run "
                    f"tools/capture_examples.py against production first")
    baseline = json.loads(path.read_text(encoding="utf-8"))
    expected_tabs = baseline["tabs"]

    actual_tabs = file_menu.open_examples().catalog()

    problems = []
    for tab in expected_tabs:
        if tab not in actual_tabs:
            problems.append(f"Tab missing: {tab!r} ({len(expected_tabs[tab])} examples)")
    for tab in actual_tabs:
        if tab not in expected_tabs:
            problems.append(f"New tab: {tab!r} ({len(actual_tabs[tab])} examples)")
    for tab in expected_tabs:
        if tab not in actual_tabs:
            continue
        missing, added = _diff(expected_tabs[tab], actual_tabs[tab])
        problems += [f"{tab}: missing {name!r}" for name in missing]
        problems += [f"{tab}: added {name!r}" for name in added]

    assert not problems, (
        f"{site.product} examples differ from the production baseline "
        f"({baseline['site']}, captured {baseline['captured']}):\n  "
        + "\n  ".join(problems)
    )
