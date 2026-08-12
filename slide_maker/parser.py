"""Split a slides.md file into per-slide frontmatter + body, and load deck.yaml."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

SLIDE_SEP_RE = re.compile(r"(?m)^\+\+\+\s*$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*\n?(.*)\Z", re.DOTALL)


class SlideMakerError(Exception):
    """Raised for any authoring/build error, tagged with a slide index when known."""

    def __init__(self, message: str, slide_index: int | None = None):
        self.slide_index = slide_index
        prefix = f"slide {slide_index + 1}: " if slide_index is not None else ""
        super().__init__(f"{prefix}{message}")


@dataclass
class RawSlide:
    index: int
    frontmatter: dict
    body: str


def parse_slides_file(path: Path) -> list[RawSlide]:
    text = path.read_text(encoding="utf-8")
    chunks = [c for c in SLIDE_SEP_RE.split(text)]
    # Drop chunks that are purely whitespace (e.g. leading/trailing blank chunk
    # from a file that starts/ends with a `+++` separator).
    chunks = [c for c in chunks if c.strip()]

    slides: list[RawSlide] = []
    for i, chunk in enumerate(chunks):
        match = FRONTMATTER_RE.match(chunk.strip("\n") + "\n")
        if not match:
            raise SlideMakerError(
                "missing YAML frontmatter (expected a `---`-fenced block at the "
                "start of the slide)",
                slide_index=i,
            )
        raw_yaml, body = match.groups()
        try:
            frontmatter = yaml.safe_load(raw_yaml) or {}
        except yaml.YAMLError as exc:
            raise SlideMakerError(f"invalid YAML frontmatter: {exc}", slide_index=i) from exc
        if not isinstance(frontmatter, dict):
            raise SlideMakerError("frontmatter must be a YAML mapping", slide_index=i)
        slides.append(RawSlide(index=i, frontmatter=frontmatter, body=body.strip()))

    if not slides:
        raise SlideMakerError("no slides found in input file")
    return slides


def load_deck_config(path: Path | None) -> dict:
    if path is None:
        return {}
    if not path.exists():
        raise SlideMakerError(f"deck config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SlideMakerError(f"deck config file must be a YAML mapping: {path}")
    return data
