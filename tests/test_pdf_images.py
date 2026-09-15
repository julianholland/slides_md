import struct
import sys
import zlib
from pathlib import Path
from unittest.mock import patch

import pytest

from slide_maker.build import build
from slide_maker.parser import SlideMakerError
from slide_maker.pdf_images import rasterize_pdf

pymupdf = pytest.importorskip("pymupdf")


def _write_pdf(path: Path, width: float = 400, height: float = 300) -> None:
    doc = pymupdf.open()
    doc.new_page(width=width, height=height)
    doc.save(path)
    doc.close()


def _write_png(path: Path, width: int, height: int) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(width) for _ in range(height))
    idat = zlib.compress(raw)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    path.write_bytes(data)


# --- rasterize_pdf unit tests --------------------------------------------------

def test_rasterize_pdf_produces_png_at_correct_dpi(tmp_path):
    pdf_path = tmp_path / "figure.pdf"
    _write_pdf(pdf_path, width=400, height=300)  # points, native 72 dpi
    out_dir = tmp_path / "out"

    png_path = rasterize_pdf(pdf_path, out_dir, dpi=200)

    assert png_path == out_dir / "figure.png"
    assert png_path.exists()
    from slide_maker import imagesize

    width, height = imagesize.get_size(png_path)
    assert abs(width - round(400 * 200 / 72)) <= 1
    assert abs(height - round(300 * 200 / 72)) <= 1


def test_rasterize_pdf_corrupt_file_raises(tmp_path):
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"not a pdf at all")

    with pytest.raises(SlideMakerError, match="could not open PDF"):
        rasterize_pdf(pdf_path, tmp_path / "out")


def test_rasterize_pdf_missing_pymupdf_raises_with_install_hint(tmp_path):
    pdf_path = tmp_path / "figure.pdf"
    _write_pdf(pdf_path)

    with patch.dict(sys.modules, {"pymupdf": None}):
        with pytest.raises(SlideMakerError, match="pdf-images"):
            rasterize_pdf(pdf_path, tmp_path / "out")


# --- end-to-end build ---------------------------------------------------------

def test_pdf_used_as_single_image(tmp_path):
    _write_pdf(tmp_path / "figure.pdf")
    src = tmp_path / "slides.md"
    src.write_text("---\nlayout: content\ntitle: X\nimage: figure.pdf\nimage_alt: A\n---\nbody\n")
    out = tmp_path / "out"

    result = build(input_path=src, output_dir=out, strict=True)

    assert result.warnings == []
    assert (out / "slide_images" / "figure.png").exists()
    assert not (out / "slide_images" / "figure.pdf").exists()
    html = (out / "index.html").read_text()
    assert 'src="slide_images/figure.png"' in html


def test_pdf_referenced_twice_rasterizes_once(tmp_path):
    _write_pdf(tmp_path / "figure.pdf")
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: A\nimage: figure.pdf\nimage_alt: A\n---\na\n"
        "+++\n---\nlayout: content\ntitle: B\nimage: figure.pdf\nimage_alt: A\n---\nb\n"
    )
    out = tmp_path / "out"

    build(input_path=src, output_dir=out, strict=True)

    assert list((out / "slide_images").glob("figure.*")) == [out / "slide_images" / "figure.png"]


def test_pdf_and_same_stem_png_collide(tmp_path):
    _write_pdf(tmp_path / "figure.pdf")
    _write_png(tmp_path / "figure.png", 50, 50)
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: A\nimage: figure.pdf\nimage_alt: A\n---\na\n"
        "+++\n---\nlayout: content\ntitle: B\nimage: figure.png\nimage_alt: A\n---\nb\n"
    )
    out = tmp_path / "out"

    with pytest.raises(SlideMakerError, match="image basename collision"):
        build(input_path=src, output_dir=out)


def test_pdf_in_images_pair_uses_rasterized_dimensions(tmp_path):
    _write_pdf(tmp_path / "a.pdf", width=400, height=900)  # tall/narrow, like the
    _write_pdf(tmp_path / "b.pdf", width=400, height=900)  # existing PNG pair test fixtures
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: Pair\n"
        "images:\n  - image: a.pdf\n    alt: A\n  - image: b.pdf\n    alt: B\n---\nbody\n"
    )
    out = tmp_path / "out"

    result = build(input_path=src, output_dir=out, strict=True)

    assert result.warnings == []
    html = (out / "index.html").read_text()
    assert 'class="image-pair side"' in html  # 0.44+0.44 ratio sum <= 1 -> side by side
    assert (out / "slide_images" / "a.png").exists()
    assert (out / "slide_images" / "b.png").exists()
