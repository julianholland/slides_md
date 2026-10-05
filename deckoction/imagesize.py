"""Minimal PNG/JPEG/GIF dimension reader.

Only reads header bytes (no pixel decode) — avoids pulling in Pillow as a
dependency just to answer "how wide/tall is this image", which is all the
image-pair layout heuristic in build.py needs.
"""

from __future__ import annotations

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
