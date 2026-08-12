import struct
import zlib
from pathlib import Path

import pytest

from slide_maker.build import build
from slide_maker.parser import SlideMakerError

DEMO_DIR = Path(__file__).resolve().parents[1] / "examples" / "demo"


def write_png(path: Path, width: int, height: int) -> None:
    """Write a minimal but real (decodable IHDR) grayscale PNG of the given size."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(width) for _ in range(height))
    idat = zlib.compress(raw)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    path.write_bytes(data)


def test_build_demo_deck(tmp_path):
    out = tmp_path / "out"
    result = build(input_path=DEMO_DIR / "slides.md", output_dir=out)

    assert result.slide_count == 7
    assert result.warnings == []

    html = (out / "index.html").read_text()
    assert html.count('<section class="slide') == 7

    # title bg + alpha content-slide bg + full-bleed image-layout slide
    assert html.count('class="bg-layer"') == 3
    assert html.count('class="formula-box"') == 1
    assert html.count('class="panel"') == 2
    assert html.count('class="slide image-slide"') == 1
    assert html.count('class="image-caption"') == 1

    # screenshot_a/b are 400x900 portraits: ratio sum 0.44+0.44 <= 1 -> side by side
    assert html.count('class="image-pair side"') == 1

    # click-to-zoom lightbox is always present, once
    assert html.count('id="lightbox"') == 1

    script = (out / "assets" / "script.js").read_text()
    assert "setZoom" in script  # click/wheel zoom inside the opened lightbox

    images = sorted(p.name for p in (out / "slide_images").iterdir())
    assert images == [
        "after.png", "before.png", "diagram.png", "hero.jpg",
        "screenshot_a.png", "screenshot_b.png", "watermark.png",
    ]

    assert (out / "vendor" / "katex" / "katex.min.js").exists()
    assert (out / "vendor" / "katex" / "auto-render.min.js").exists()
    assert (out / "assets" / "style.css").exists()
    assert (out / "assets" / "script.js").exists()


def test_blockquote_matches_body_text_size_and_wraps(tmp_path):
    out = tmp_path / "out"
    build(input_path=DEMO_DIR / "slides.md", output_dir=out)
    css = (out / "assets" / "style.css").read_text()

    bullets_rule = css[css.index("ul.bullets {"):css.index("}", css.index("ul.bullets {"))]
    assert "font-size: 1.6rem;" in bullets_rule

    blockquote_rule = css[css.index("blockquote,"):css.index("}", css.index("blockquote,"))]
    assert "font-size: 1.6rem;" in blockquote_rule
    assert "overflow-wrap: break-word;" in blockquote_rule


def test_background_image_uses_inline_style_not_css_custom_property(tmp_path):
    # Regression test: a url() inside a CSS custom property resolves relative to
    # the stylesheet that consumes it via var() (assets/style.css), not the HTML
    # page — which breaks resolution against slide_images/ at the output root.
    # background-image/opacity must be set directly as inline styles instead.
    out = tmp_path / "out"
    build(input_path=DEMO_DIR / "slides.md", output_dir=out)

    html = (out / "index.html").read_text()
    assert "--bg-image" not in html
    assert "background-image: url('slide_images/hero.jpg')" in html

    css = (out / "assets" / "style.css").read_text()
    assert "--bg-image" not in css
    assert "--bg-opacity" not in css


def test_image_layout_fills_slide_with_no_caption_when_title_omitted(tmp_path):
    src = tmp_path / "slides.md"
    (tmp_path / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    src.write_text("---\nlayout: image\nimage: img.png\nimage_alt: a photo\n---\n")

    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []

    html = (tmp_path / "out" / "index.html").read_text()
    assert 'class="slide image-slide"' in html
    assert "background-image: url('slide_images/img.png')" in html
    assert 'role="img" aria-label="a photo"' in html
    assert "image-caption" not in html
    assert "background-size: contain;" in html  # fit defaults to "contain"


def test_image_layout_fit_cover_fills_the_screen(tmp_path):
    src = tmp_path / "slides.md"
    (tmp_path / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    src.write_text("---\nlayout: image\nimage: img.png\nimage_alt: a photo\nfit: cover\n---\n")

    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []
    html = (tmp_path / "out" / "index.html").read_text()
    assert "background-size: cover;" in html


def test_image_layout_invalid_fit_rejected(tmp_path):
    src = tmp_path / "slides.md"
    (tmp_path / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    src.write_text("---\nlayout: image\nimage: img.png\nimage_alt: a photo\nfit: zoom\n---\n")
    with pytest.raises(SlideMakerError, match="invalid fit"):
        build(input_path=src, output_dir=tmp_path / "out")


def test_fit_on_non_image_layout_warns(tmp_path):
    src = tmp_path / "slides.md"
    src.write_text("---\nlayout: content\ntitle: A\nfit: cover\n---\nbody\n")
    result = build(input_path=src, output_dir=tmp_path / "out")
    assert any("fit" in w for w in result.warnings)


def test_image_pair_stacks_when_wider_images(tmp_path):
    write_png(tmp_path / "a.png", 1600, 900)  # ratio 1.78
    write_png(tmp_path / "b.png", 900, 700)  # ratio 1.29, sum 3.06 > 1 -> stack
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: Pair\n"
        "images:\n  - image: a.png\n    alt: A\n  - image: b.png\n    alt: B\n---\nbody\n"
    )
    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []
    html = (tmp_path / "out" / "index.html").read_text()
    assert 'class="image-pair stack"' in html
    assert html.count("<img") == 3  # 2 content images + the lightbox's empty <img>
    assert 'id="lightbox"' in html


def test_image_pair_sits_side_by_side_when_narrow_images(tmp_path):
    write_png(tmp_path / "a.png", 400, 900)  # ratio 0.44
    write_png(tmp_path / "b.png", 400, 900)  # ratio 0.44, sum 0.89 <= 1 -> side
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: Pair\n"
        "images:\n  - image: a.png\n    alt: A\n  - image: b.png\n    alt: B\n---\nbody\n"
    )
    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []
    html = (tmp_path / "out" / "index.html").read_text()
    assert 'class="image-pair side"' in html


def test_single_image_label_renders_as_caption(tmp_path):
    write_png(tmp_path / "a.png", 400, 300)
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: Labeled\n"
        "image: a.png\nimage_alt: A\nimage_label: Figure 1\n---\nbody\n"
    )
    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []
    html = (tmp_path / "out" / "index.html").read_text()
    assert 'class="media-item"' in html
    assert '<div class="panel-label">Figure 1</div>' in html


def test_image_pair_labels_render_per_item(tmp_path):
    write_png(tmp_path / "a.png", 400, 900)
    write_png(tmp_path / "b.png", 400, 900)
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: Pair\n"
        "images:\n"
        "  - image: a.png\n    alt: A\n    label: Before\n"
        "  - image: b.png\n    alt: B\n    label: After\n"
        "---\nbody\n"
    )
    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []
    html = (tmp_path / "out" / "index.html").read_text()
    assert html.count('class="image-pair-item"') == 2
    assert '<div class="panel-label">Before</div>' in html
    assert '<div class="panel-label">After</div>' in html


def test_images_requires_exactly_two(tmp_path):
    write_png(tmp_path / "a.png", 400, 900)
    src = tmp_path / "slides.md"
    src.write_text("---\nlayout: content\ntitle: Pair\nimages:\n  - image: a.png\n---\nbody\n")
    with pytest.raises(SlideMakerError, match="exactly 2 images"):
        build(input_path=src, output_dir=tmp_path / "out")


def test_images_mutually_exclusive_with_image(tmp_path):
    write_png(tmp_path / "a.png", 400, 900)
    write_png(tmp_path / "b.png", 400, 900)
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: Pair\nimage: a.png\nimage_alt: x\n"
        "images:\n  - image: a.png\n    alt: A\n  - image: b.png\n    alt: B\n---\nbody\n"
    )
    with pytest.raises(SlideMakerError, match="image/panels/video/images"):
        build(input_path=src, output_dir=tmp_path / "out")


def test_images_missing_alt_warns(tmp_path):
    write_png(tmp_path / "a.png", 400, 900)
    write_png(tmp_path / "b.png", 400, 900)
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: Pair\n"
        "images:\n  - image: a.png\n  - image: b.png\n---\nbody\n"
    )
    result = build(input_path=src, output_dir=tmp_path / "out")
    assert any("images[0]" in w for w in result.warnings)
    assert any("images[1]" in w for w in result.warnings)


def test_image_layout_requires_image_field(tmp_path):
    src = tmp_path / "slides.md"
    src.write_text("---\nlayout: image\ntitle: No image here\n---\n")
    with pytest.raises(SlideMakerError, match="requires an 'image' field"):
        build(input_path=src, output_dir=tmp_path / "out")


def test_image_layout_rejects_redundant_background(tmp_path):
    src = tmp_path / "slides.md"
    (tmp_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "b.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    src.write_text("---\nlayout: image\nimage: a.png\nbackground: b.png\n---\n")
    with pytest.raises(SlideMakerError, match="redundant"):
        build(input_path=src, output_dir=tmp_path / "out")


def test_build_fails_on_missing_image(tmp_path):
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: A\nimage: does_not_exist.png\nimage_alt: x\n---\nbody\n"
    )
    with pytest.raises(SlideMakerError, match="does_not_exist.png"):
        build(input_path=src, output_dir=tmp_path / "out")


def test_build_refuses_nonempty_output_without_force(tmp_path):
    out = tmp_path / "out"
    build(input_path=DEMO_DIR / "slides.md", output_dir=out)
    with pytest.raises(SlideMakerError, match="not empty"):
        build(input_path=DEMO_DIR / "slides.md", output_dir=out)
    # force overwrite succeeds
    build(input_path=DEMO_DIR / "slides.md", output_dir=out, force=True)


def test_strict_promotes_missing_alt_warning_to_error(tmp_path):
    src = tmp_path / "slides.md"
    (tmp_path / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    src.write_text(
        "---\nlayout: content\ntitle: A\nimage: img.png\n---\nbody\n"
    )
    with pytest.raises(SlideMakerError):
        build(input_path=src, output_dir=tmp_path / "out", strict=True)
    # non-strict just warns
    result = build(input_path=src, output_dir=tmp_path / "out2")
    assert any("image_alt" in w for w in result.warnings)
