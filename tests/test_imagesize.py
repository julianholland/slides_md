import struct
import zlib
from pathlib import Path

import pytest

from deckoction.imagesize import ImageSizeError, get_size

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


@pytest.mark.parametrize(
    "root, expected",
    [
        ('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">', (400, 300)),
        ('<svg width="4in" height="3in">', (384, 288)),
        ('<svg width="4in" height="288px">', (384, 288)),
        ('<svg viewBox="0 0 800 600">', (800, 600)),
        ('<svg viewBox="0,0,800,600">', (800, 600)),
        ('<svg width="100%" height="100%" viewBox="0 0 160 90">', (160, 90)),
        ("<svg\n  height='50'\n  width='200'>", (200, 50)),
    ],
)
def test_get_size_svg(tmp_path, root, expected):
    p = tmp_path / "a.svg"
    p.write_text(root + "<rect/></svg>")
    assert get_size(p) == expected


def test_get_size_svg_after_prolog_and_comment(tmp_path):
    p = tmp_path / "a.svg"
    p.write_bytes(
        b'\xef\xbb\xbf<?xml version="1.0"?>\n<!-- made by hand -->\n'
        b'<!DOCTYPE svg>\n<svg viewBox="0 0 30 10"></svg>'
    )
    assert get_size(p) == (30, 10)


def test_get_size_svg_without_size_or_viewbox(tmp_path):
    p = tmp_path / "a.svg"
    p.write_text('<svg width="100%"><rect/></svg>')
    with pytest.raises(ImageSizeError, match="no usable width/height or viewBox"):
        get_size(p)
