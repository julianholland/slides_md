import struct
import zlib
from pathlib import Path

import pytest

from slide_maker.imagesize import ImageSizeError, get_size

DEMO_IMAGES = Path(__file__).resolve().parents[1] / "examples" / "demo" / "images"


def write_png(path: Path, width: int, height: int) -> None:
    """Write a minimal but real (decodable IHDR) grayscale PNG of the given size."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(width) for _ in range(height))
    idat = zlib.compress(raw)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    path.write_bytes(data)


def test_get_size_png(tmp_path):
    write_png(tmp_path / "a.png", 320, 240)
    assert get_size(tmp_path / "a.png") == (320, 240)


def test_get_size_jpeg_against_real_file():
    # hero.jpg is a real generated JPEG shipped with the demo deck; dimensions
    # are known from when it was created (1600x900).
    assert get_size(DEMO_IMAGES / "hero.jpg") == (1600, 900)


def test_get_size_unsupported_format(tmp_path):
    p = tmp_path / "not_an_image.txt"
    p.write_bytes(b"just some bytes")
    with pytest.raises(ImageSizeError):
        get_size(p)
