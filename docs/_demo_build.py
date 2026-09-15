"""Builds the docs/demo/* source decks into _static/demo/ for layout-gallery.md's
iframes. Called from conf.py at import time — see the comment there for why."""

import sys
from pathlib import Path

from slide_maker.build import build

DEMO_SRC = Path(__file__).parent / "demo"
DEMO_OUT = Path(__file__).parent / "_static" / "demo"

DECK_NAMES = ("full", "title", "content", "stacked", "split", "image", "phase_in", "references")


def build_all_demo_decks() -> None:
    for name in DECK_NAMES:
        src = DEMO_SRC / name / "slides.md"
        out = DEMO_OUT / name
        try:
            build(
                src,
                out,
                config_path=DEMO_SRC / "deck.yaml",
                images_dir=DEMO_SRC / "images",
                strict=True,
                force=True,
            )
        except Exception as exc:  # noqa: BLE001 — a broken demo deck must never break the docs build
            print(f"warning: docs demo deck {name!r} failed to build: {exc}", file=sys.stderr)
