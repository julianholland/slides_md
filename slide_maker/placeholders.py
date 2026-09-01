"""LaTeX-`mwe`-style placeholder images: `example-image`, `example-image-a` .. `-z`.

Lets an author write `image: example-image-a` (no file needed) and get a
pre-generated box-outline-with-letter placeholder instead — useful while
drafting a deck before real assets exist. See scripts/generate_placeholders.py
for how the bundled PNGs were produced.
"""

from __future__ import annotations

import re
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PLACEHOLDER_DIR = PACKAGE_DIR / "placeholder_images"

_NAME_RE = re.compile(r"^example-image(-([a-z]))?$")


def resolve_placeholder(name: str) -> Path | None:
    """Return the bundled placeholder file for a name like 'example-image-a', or None."""
    match = _NAME_RE.match(name.strip().lower())
    if not match:
        return None
    letter = match.group(2)
    filename = f"example-image-{letter}.png" if letter else "example-image.png"
    return PLACEHOLDER_DIR / filename


def placeholder_alt(name: str) -> str | None:
    """Default alt text for a placeholder name, or None if it isn't one."""
    match = _NAME_RE.match(name.strip().lower())
    if not match:
        return None
    letter = match.group(2)
    return f"Placeholder image {letter.upper()}" if letter else "Placeholder image"
