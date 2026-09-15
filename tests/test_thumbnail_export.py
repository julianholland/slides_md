from pathlib import Path

import pytest

from slide_maker import imagesize
from slide_maker.build import build
from slide_maker.thumbnail import export_thumbnail

DEMO_DIR = Path(__file__).resolve().parents[1] / "examples" / "demo"

playwright_sync_api = pytest.importorskip("playwright.sync_api")


def _chromium_available() -> bool:
    try:
        with playwright_sync_api.sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _chromium_available(), reason="Playwright Chromium browser is not installed"
)


def test_export_thumbnail_screenshots_first_slide(tmp_path):
    out = tmp_path / "out"
    build(input_path=DEMO_DIR / "slides.md", output_dir=out)

    thumbnail_path = tmp_path / "thumbnail.png"
    export_thumbnail(out, thumbnail_path, viewport=(800, 450))

    assert thumbnail_path.exists()
    assert thumbnail_path.stat().st_size > 0
    assert imagesize.get_size(thumbnail_path) == (800, 450)


def test_export_thumbnail_creates_missing_parent_dirs(tmp_path):
    out = tmp_path / "out"
    build(input_path=DEMO_DIR / "slides.md", output_dir=out)

    thumbnail_path = tmp_path / "nested" / "dir" / "thumbnail.png"
    export_thumbnail(out, thumbnail_path)

    assert thumbnail_path.exists()
