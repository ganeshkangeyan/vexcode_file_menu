"""
Per-site settings for every VEXcode web product this suite runs against.

The tests and page objects are shared across all sites -- the File menu
works the same way everywhere. Only the *data* differs between products
(file extensions, which text languages exist, the Open Examples catalog,
etc.), and that data lives here, one SiteConfig per site.

Every value below was captured from the live site (2026-10-24) by driving
the real app with the suite's own Save/Open mocks -- e.g. extensions are
the `suggestedName` the app itself passed to showSaveFilePicker(), example
counts are the real number of cards per category tab.

Adding a new site = add one SiteConfig entry + capture its fixture files
with tools/capture_fixtures.py. No test code changes needed.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

FIXTURES_ROOT = Path(__file__).parent / "tests" / "fixtures"


@dataclass(frozen=True)
class SiteConfig:
    key: str                 # short id, also the fixtures sub-folder name
    product: str             # e.g. "VEXcode V5" -- page <title>
    extensions: dict         # mode -> file extension; only modes the site supports

    # --- New Text Project flow ---
    # True: File > New Text Project opens the "Select a Project Language"
    # dialog. False: it goes straight into the only text language (GO).
    language_dialog: bool = True
    # Some products ask "Select a Project Type" (EXP: EXP Brain / 6-Axis
    # Arm) after the language on New Text Project AND on every New Blocks
    # Project. The button to pick, or None when the product doesn't ask.
    project_type_choice: Optional[str] = None
    # Text that must appear in a fresh project's boilerplate, per language.
    text_markers: dict = field(default_factory=dict)

    # --- Open Examples ---
    example_categories: tuple = ()
    example_count: int = 0

    # --- Fixture files (real projects exported from the app) ---
    # mode -> filename for the File > Open tests, plus 6 distinct files
    # (oldest first) for the Open Recent "keep last 5" test.
    open_fixtures: dict = field(default_factory=dict)
    recent_fixtures: tuple = ()

    # ---------------------------------------------------------------
    @property
    def text_languages(self) -> list:
        return [m for m in self.extensions if m != "blocks"]

    def supports(self, mode: str) -> bool:
        return mode in self.extensions

    def mode_for_file(self, path: Path) -> str:
        for mode, ext in self.extensions.items():
            if path.suffix == ext:
                return mode
        raise ValueError(f"{path.name} is not a {self.product} project file")

    @property
    def fixtures_dir(self) -> Path:
        return FIXTURES_ROOT / self.key

    def fixture(self, mode: str) -> Path:
        return self.fixtures_dir / self.open_fixtures[mode]

    def recent_fixture_paths(self) -> list:
        return [self.fixtures_dir / name for name in self.recent_fixtures]


PY_VEX = "from vex import *"
CPP_VEX = '#include "vex.h"'

SITES = {
    "codev5.vex.com": SiteConfig(
        key="v5",
        product="VEXcode V5",
        extensions={"blocks": ".v5blocks", "python": ".v5python", "cpp": ".v5cpp"},
        text_markers={"python": PY_VEX, "cpp": CPP_VEX},
        example_categories=(
            "All", "Templates", "Motion", "Drivetrain", "Looks", "Magnet", "Arm",
            "Events", "Control", "Sensing", "Operators", "Variables", "My Blocks",
        ),
        example_count=94,
        open_fixtures={
            "blocks": "Printing Lines and Shapes.v5blocks",
            "python": "Changing Velocities.v5python",
            "cpp": "Complex Decisions (AND OR NOT).v5cpp",
        },
        recent_fixtures=(
            "Printing Lines and Shapes.v5blocks",
            "Changing Velocities.v5python",
            "Complex Decisions (AND OR NOT).v5cpp",
            "Exampleproject3.v5blocks",
            "Printing Text.v5blocks",
            "Using Sensors and Loops.v5blocks",
        ),
    ),
    "code123.vex.com": SiteConfig(
        key="123",
        product="VEXcode 123",
        extensions={"blocks": ".123blocks"},  # blocks only -- no New Text Project
        language_dialog=False,
        example_categories=(
            "All", "Drivetrain", "Looks", "Sound", "Actions", "Events", "Control",
            "Sensing", "Operators", "Variables", "My Blocks",
        ),
        example_count=17,
    ),
    "codego.vex.com": SiteConfig(
        key="go",
        product="VEXcode GO",
        extensions={"blocks": ".goblocks", "python": ".gopython"},
        language_dialog=False,  # New Text Project goes straight to Python
        text_markers={"python": "from go import *"},
        example_categories=(
            "All", "Templates", "Motion", "Drivetrain", "Magnet", "Looks", "Events",
            "Control", "Sensing", "Operators", "Variables", "My Blocks",
        ),
        example_count=26,
    ),
    "codeexp.vex.com": SiteConfig(
        key="exp",
        product="VEXcode EXP",
        extensions={"blocks": ".expblocks", "python": ".exppython", "cpp": ".expcpp"},
        project_type_choice="EXP Brain",
        text_markers={"python": PY_VEX, "cpp": CPP_VEX},
        example_categories=(
            "All", "Templates", "Motion", "Drivetrain", "Looks", "Sound", "Magnet",
            "Arm", "Events", "Control", "Sensing", "Operators", "Variables", "My Blocks",
        ),
        example_count=80,
    ),
    "codeiq.vex.com": SiteConfig(
        key="iq",
        product="VEXcode IQ",
        extensions={"blocks": ".iqblocks", "python": ".iqpython", "cpp": ".iqcpp"},
        text_markers={"python": PY_VEX, "cpp": CPP_VEX},
        example_categories=(
            "All", "Templates", "Motion", "Drivetrain", "Looks", "Sound", "Events",
            "Control", "Sensing", "Operators", "Variables", "My Blocks",
        ),
        example_count=75,
    ),
}


def _with_captured_fixtures(cfg: SiteConfig) -> SiteConfig:
    """Sites other than V5 use fixtures captured by tools/capture_fixtures.py,
    which writes a manifest.json next to them -- read it so this file
    doesn't have to repeat the captured filenames by hand."""
    if cfg.open_fixtures:
        return cfg
    manifest = cfg.fixtures_dir / "manifest.json"
    if not manifest.exists():
        return cfg
    import json
    from dataclasses import replace
    data = json.loads(manifest.read_text(encoding="utf-8"))
    return replace(cfg, open_fixtures=data["open"], recent_fixtures=tuple(data["recent"]))


def site_for_url(url: str) -> SiteConfig:
    host = urlparse(url).hostname or ""
    # staging.codev5.vex.com etc. share their product's settings
    for known, cfg in SITES.items():
        if host == known or host.endswith("." + known):
            return _with_captured_fixtures(cfg)
    raise KeyError(
        f"No site settings for {host!r}. Add a SiteConfig for it in sites.py "
        f"(known: {', '.join(SITES)})."
    )
