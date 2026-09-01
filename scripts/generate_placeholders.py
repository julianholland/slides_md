#!/usr/bin/env python3
"""One-off generator for the bundled `example-image[-a..z]` placeholder PNGs.

Dev-only tool (not part of the installed package, not a runtime dependency —
requires Pillow, which slide_maker itself does not depend on). Run this again
and re-commit the output if the placeholder style needs to change:

    python3 scripts/generate_placeholders.py
"""

from __future__ import annotations

import string
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parent.parent / "slide_maker" / "placeholder_images"

SIZE = 640
MARGIN = 18
BG = (230, 230, 226)
BORDER = (60, 63, 71)
LETTER = (60, 63, 71)
BORDER_WIDTH = 6
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def render(letter: str | None, path: Path) -> None:
    img = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle(
        [MARGIN, MARGIN, SIZE - MARGIN, SIZE - MARGIN],
        outline=BORDER,
        width=BORDER_WIDTH,
    )
    if letter:
        font = ImageFont.truetype(FONT_PATH, size=int(SIZE * 0.45))
        bbox = draw.textbbox((0, 0), letter, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            (SIZE / 2 - w / 2 - bbox[0], SIZE / 2 - h / 2 - bbox[1]),
            letter,
            fill=LETTER,
            font=font,
        )
    img.save(path)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render(None, OUT_DIR / "example-image.png")
    for letter in string.ascii_lowercase:
        render(letter.upper(), OUT_DIR / f"example-image-{letter}.png")
    print(f"wrote {1 + 26} placeholder images to {OUT_DIR}")


if __name__ == "__main__":
    main()
