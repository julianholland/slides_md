"""Minimal PNG/JPEG/GIF/SVG dimension reader.

Only reads header bytes (no pixel decode) — avoids pulling in Pillow as a
dependency just to answer "how wide/tall is this image", which is all the
image-grid arrangement in build.py needs. SVG sizes come from the root `<svg>`
tag's `width`/`height` (absolute units) or else its `viewBox`, read with a regex
rather than an XML parser (no entity expansion, no dependency).
"""

from __future__ import annotations

import re
import struct
from pathlib import Path


class ImageSizeError(Exception):
    pass


def get_size(path: Path) -> tuple[int, int]:
    data = Path(path).read_bytes()

    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return width, height

    if data[:6] in (b"GIF87a", b"GIF89a"):
        width, height = struct.unpack("<HH", data[6:10])
        return width, height

    if data[:2] == b"\xff\xd8":
        return _jpeg_size(data, path)

    svg_tag = _SVG_ROOT_RE.search(data[:_SVG_SNIFF_BYTES])
    if svg_tag is not None:
        return _svg_size(svg_tag.group(0).decode("utf-8", "replace"), path)

    raise ImageSizeError(f"unsupported image format for size detection: {path}")


_JPEG_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
}


def _jpeg_size(data: bytes, path: Path) -> tuple[int, int]:
    idx = 2
    length = len(data)
    while idx + 9 <= length:
        if data[idx] != 0xFF:
            raise ImageSizeError(f"malformed JPEG (bad marker): {path}")
        marker = data[idx + 1]
        if marker in _JPEG_SOF_MARKERS:
            height, width = struct.unpack(">HH", data[idx + 5:idx + 9])
            return width, height
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            idx += 2
            continue
        seg_len = struct.unpack(">H", data[idx + 2:idx + 4])[0]
        idx += 2 + seg_len
    raise ImageSizeError(f"could not find JPEG dimensions: {path}")


# The root tag sits after an optional BOM, `<?xml ...?>`, comments and doctype; this
# only needs to find it, not validate what precedes it.
_SVG_SNIFF_BYTES = 64 * 1024
_SVG_ROOT_RE = re.compile(rb"<svg\b[^>]*>", re.IGNORECASE)
_SVG_LENGTH_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+(?:e[+-]?[0-9]+)?)\s*(px|pt|pc|mm|cm|in)?\s*$", re.IGNORECASE)
# CSS absolute units -> px, so e.g. width="4in" height="300px" still gives the right ratio.
_SVG_UNIT_PX = {"": 1.0, "px": 1.0, "pt": 4 / 3, "pc": 16.0, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96.0}


def _svg_attr(tag: str, name: str) -> str | None:
    match = re.search(rf"""\s{name}\s*=\s*(["'])(.*?)\1""", tag, re.IGNORECASE | re.DOTALL)
    return match.group(2) if match else None


def _svg_length(value: str | None) -> float | None:
    """An absolute length in px, or None for missing/relative (`%`, `em`, ...) values."""
    match = _SVG_LENGTH_RE.match(value) if value else None
    if match is None:
        return None
    return float(match.group(1)) * _SVG_UNIT_PX[(match.group(2) or "").lower()]


def _svg_size(tag: str, path: Path) -> tuple[int, int]:
    width = _svg_length(_svg_attr(tag, "width"))
    height = _svg_length(_svg_attr(tag, "height"))
    if not (width and height):
        view_box = _svg_attr(tag, "viewBox")
        parts = re.split(r"[\s,]+", view_box.strip()) if view_box else []
        try:
            width, height = float(parts[2]), float(parts[3])
        except (IndexError, ValueError):
            raise ImageSizeError(f"SVG has no usable width/height or viewBox: {path}") from None
    if width <= 0 or height <= 0:
        raise ImageSizeError(f"SVG has a non-positive size: {path}")
    return max(1, round(width)), max(1, round(height))
