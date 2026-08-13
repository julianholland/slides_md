"""Exercises the same build path docs/_demo_build.py uses for the layout-gallery
page, so a broken docs demo deck (e.g. a missing image_alt) is caught by `pytest`
without needing a full Sphinx build."""

from pathlib import Path

import pytest

from slide_maker.build import build

DEMO_SRC = Path(__file__).resolve().parents[1] / "docs" / "demo"
DECK_NAMES = ("full", "title", "content", "stacked", "split", "image")


@pytest.mark.parametrize("name", DECK_NAMES)
def test_docs_demo_deck_builds_clean(tmp_path, name):
    result = build(
        input_path=DEMO_SRC / name / "slides.md",
        output_dir=tmp_path / name,
        config_path=DEMO_SRC / "deck.yaml",
        images_dir=DEMO_SRC / "images",
        strict=True,
        force=True,
    )
    assert result.warnings == []
    assert result.slide_count > 0
    assert (tmp_path / name / "index.html").exists()


def test_full_demo_deck_exercises_all_five_layouts(tmp_path):
    result = build(
        input_path=DEMO_SRC / "full" / "slides.md",
        output_dir=tmp_path / "full",
        config_path=DEMO_SRC / "deck.yaml",
        images_dir=DEMO_SRC / "images",
        strict=True,
        force=True,
    )
    assert result.slide_count == 7

    html = (tmp_path / "full" / "index.html").read_text()
    assert html.count('class="slide title-slide"') == 1
    assert html.count('class="slide image-slide"') == 1
    assert html.count('class="formula-box"') == 1
    assert html.count('class="split-panels"') == 1
