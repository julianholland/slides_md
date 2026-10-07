import struct
import zlib
from pathlib import Path

import pytest

from deckoction.build import arrange_images, build
from deckoction.parser import SlideMakerError

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


def grid_rows(html: str) -> list[int]:
    """Images per `.image-grid-row`, in document order, across the whole deck."""
    return [chunk.split("</section>")[0].count('class="image-grid-item"') for chunk in html.split('class="image-grid-row"')[1:]]


def test_build_demo_deck(tmp_path):
    out = tmp_path / "out"
    result = build(input_path=DEMO_DIR / "slides.md", output_dir=out)

    # 13 authored slides; the phase-in content slide (3 bullets) expands to 4 physical
    # slides, the phase-in split slide (3 panels) to 4, the phase-in image slide
    # (3 phase_images) to 3
    assert result.slide_count == 21
    assert result.warnings == []

    html = (out / "index.html").read_text()
    assert html.count('<section class="slide') == 21
    # every phase-in slide's physical steps share one display number
    assert html.count('data-display-index="5"') == 4
    assert html.count('data-display-index="11"') == 4
    assert html.count('data-display-index="12"') == 3

    # citations: cited once in body text + once via image_reference, same key -> 1 ref
    assert html.count('<sup class="citation">[1]</sup>') == 1
    assert html.count('class="citation-badge">1</span>') == 1
    assert html.count('<span class="ref-num">1.</span>') == 1

    # title bg + alpha content-slide bg + full-bleed image-layout slide + 3 image cycle steps
    assert html.count('class="bg-layer"') == 6
    assert html.count('class="formula-box"') == 1
    # the `equation` slide + the phase-in content slide's equation step
    assert html.count('class="media-equation"') == 2
    assert html.count("<table>") == 1
    # plain split: 2; phase-in split: 1 current panel on each of 3 steps + 3 on the final
    assert html.count('class="panel"') == 8
    assert html.count('class="panel phase-pending"') == 3
    assert html.count('class="panel phase-dim"') == 3
    assert html.count('class="slide image-slide"') == 4
    assert html.count('class="image-caption"') == 4

    # screenshot_a/b are 400x900 portraits -> one row, side by side
    assert html.count('class="image-grid"') == 3  # the `images` slide + 2 phase-in group steps

    # click-to-zoom lightbox is always present, once
    assert html.count('id="lightbox"') == 1

    script = (out / "assets" / "script.js").read_text()
    assert "setZoom" in script  # click/wheel zoom inside the opened lightbox

    assert 'src="slide_images/example-image-c.png"' in html
    assert 'alt="Placeholder image C"' in html

    # <!-- --> comments are stripped: an inline note and a whole commented-out
    # draft slide (which would otherwise make this 9 slides, not 8)
    assert "TODO" not in html
    assert "Draft slide, not ready yet" not in html

    images = sorted(p.name for p in (out / "slide_images").iterdir())
    assert images == [
        "after.png", "before.png", "diagram.png", "example-image-a.png",
        "example-image-b.png", "example-image-c.png", "example-image-d.png", "hero.jpg",
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


def test_table_has_body_scoped_style(tmp_path):
    out = tmp_path / "out"
    build(input_path=DEMO_DIR / "slides.md", output_dir=out)
    css = (out / "assets" / "style.css").read_text()
    assert ".text-col table," in css
    assert ".slide-body.stacked > table {" in css


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


@pytest.mark.parametrize(
    "fields",
    [
        "layout: content\ntitle: T",
        "layout: stacked\ntitle: T",
        "layout: split\ntitle: T\npanels:\n  - image: example-image\n    label: L",
        "layout: image\ntitle: T\nimage: example-image",
        "layout: references\ntitle: T",
    ],
)
def test_subtitle_renders_below_title_on_every_layout(tmp_path, fields):
    src = tmp_path / "slides.md"
    src.write_text(f"---\n{fields}\nsubtitle: Sub line\n---\n\n- body\n")
    result = build(input_path=src, output_dir=tmp_path / "out", strict=True)
    assert result.warnings == []
    html = (tmp_path / "out" / "index.html").read_text()
    assert '<h1>T</h1><p class="subtitle">Sub line</p>' in html


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
    assert grid_rows(html) == [1, 1]  # stacked
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
    assert grid_rows(html) == [2]  # side by side


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
    assert html.count('class="image-grid-item"') == 2
    assert '<div class="panel-label">Before</div>' in html
    assert '<div class="panel-label">After</div>' in html


def test_images_requires_at_least_two(tmp_path):
    write_png(tmp_path / "a.png", 400, 900)
    src = tmp_path / "slides.md"
    src.write_text("---\nlayout: content\ntitle: Pair\nimages:\n  - image: a.png\n---\nbody\n")
    with pytest.raises(SlideMakerError, match="needs at least 2 images"):
        build(input_path=src, output_dir=tmp_path / "out")


@pytest.mark.parametrize(
    ("ratios", "rows"),
    [
        ([1, 1, 1], [3]),
        ([1, 1, 1, 1], [2, 2]),
        ([16 / 9, 16 / 9], [1, 1]),
        ([0.8, 0.8], [2]),
        ([1] * 6, [3, 3]),
        ([16 / 9] * 4, [2, 2]),
    ],
)
def test_arrange_images(ratios, rows):
    assert arrange_images(ratios) == rows


def test_arrange_images_sizes_always_cover_every_image_in_order():
    for n in range(1, 9):
        assert sum(arrange_images([1.3] * n)) == n


def test_four_images_build_a_two_by_two_grid_in_source_order(tmp_path):
    for name in "abcd":
        write_png(tmp_path / f"{name}.png", 400, 400)
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: Grid\nimages:\n"
        + "".join(f"  - image: {n}.png\n    alt: {n}\n" for n in "abcd")
        + "---\nbody\n"
    )
    build(input_path=src, output_dir=tmp_path / "out", strict=True)
    html = (tmp_path / "out" / "index.html").read_text()
    assert grid_rows(html) == [2, 2]
    positions = [html.index(f'src="slide_images/{n}.png"') for n in "abcd"]
    assert positions == sorted(positions)


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


def test_placeholder_image_needs_no_real_file(tmp_path):
    src = tmp_path / "slides.md"
    src.write_text("---\nlayout: content\ntitle: A\nimage: example-image-a\n---\nbody\n")

    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []  # placeholder auto-supplies alt text, no warning

    html = (tmp_path / "out" / "index.html").read_text()
    assert 'src="slide_images/example-image-a.png"' in html
    assert 'alt="Placeholder image A"' in html
    assert (tmp_path / "out" / "slide_images" / "example-image-a.png").is_file()


def test_placeholder_explicit_alt_wins(tmp_path):
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: A\nimage: example-image-a\nimage_alt: My own caption\n---\nbody\n"
    )
    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []
    html = (tmp_path / "out" / "index.html").read_text()
    assert 'alt="My own caption"' in html


def test_placeholder_bare_example_image(tmp_path):
    src = tmp_path / "slides.md"
    src.write_text("---\nlayout: image\nimage: example-image\n---\n")
    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []
    html = (tmp_path / "out" / "index.html").read_text()
    assert "background-image: url('slide_images/example-image.png')" in html
    assert 'aria-label="Placeholder image"' in html


def test_placeholder_in_images_pair(tmp_path):
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: Pair\n"
        "images:\n  - image: example-image-a\n  - image: example-image-b\n---\nbody\n"
    )
    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []
    html = (tmp_path / "out" / "index.html").read_text()
    assert 'src="slide_images/example-image-a.png"' in html
    assert 'src="slide_images/example-image-b.png"' in html
    assert 'alt="Placeholder image A"' in html
    assert 'alt="Placeholder image B"' in html


def test_placeholder_in_split_panels(tmp_path):
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: split\ntitle: Panels\n"
        "panels:\n  - image: example-image-a\n    label: Before\n"
        "  - image: example-image-b\n    label: After\n---\n"
    )
    result = build(input_path=src, output_dir=tmp_path / "out")
    assert result.warnings == []
    html = (tmp_path / "out" / "index.html").read_text()
    assert 'alt="Placeholder image A"' in html
    assert 'alt="Placeholder image B"' in html


def test_placeholder_not_confused_with_real_missing_file(tmp_path):
    src = tmp_path / "slides.md"
    src.write_text(
        "---\nlayout: content\ntitle: A\nimage: example-image-1\nimage_alt: x\n---\nbody\n"
    )
    with pytest.raises(SlideMakerError, match="referenced image not found"):
        build(input_path=src, output_dir=tmp_path / "out")


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


def _build_one(tmp_path, deck, strict=False):
    src = tmp_path / "slides.md"
    src.write_text(deck)
    out = tmp_path / "out"
    result = build(input_path=src, output_dir=out, strict=strict)
    return result, (out / "index.html").read_text()


def test_equation_renders_in_media_col(tmp_path):
    deck = "---\nlayout: content\ntitle: Eq\nequation: $a^2+b^2=c^2$\n---\n\n- point\n"
    result, html = _build_one(tmp_path, deck, strict=True)
    assert not result.warnings
    media = html.split('class="media-col"')[1]
    assert media.lstrip(">").strip().startswith('<div class="media-equation">$$a^2+b^2=c^2$$</div>')
    assert "<img" not in media.split("</section>")[0]


def test_equation_is_html_escaped(tmp_path):
    deck = "---\nlayout: content\ntitle: Eq\nequation: a < b\n---\n"
    _, html = _build_one(tmp_path, deck)
    assert '<div class="media-equation">$$a &lt; b$$</div>' in html


def test_equation_and_image_are_mutually_exclusive(tmp_path):
    deck = "---\nlayout: content\ntitle: Eq\nequation: a\nimage: example-image\n---\n"
    with pytest.raises(SlideMakerError, match="may only set one of"):
        _build_one(tmp_path, deck)


def test_equation_rejected_outside_content_layout(tmp_path):
    deck = "---\nlayout: stacked\ntitle: Eq\nequation: a\n---\n"
    with pytest.raises(SlideMakerError, match="equation is only used by layout 'content'"):
        _build_one(tmp_path, deck)


def test_svg_images_work_everywhere_including_the_grid(tmp_path):
    (tmp_path / "wide.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100"></svg>')
    (tmp_path / "tall.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="400"></svg>')
    deck = (
        "---\nlayout: content\ntitle: One\nimage: wide.svg\nimage_alt: w\nbackground: tall.svg\n---\n"
        "+++\n---\nlayout: content\ntitle: Grid\nimages:\n"
        "  - image: wide.svg\n    alt: w\n  - image: tall.svg\n    alt: t\n---\n"
    )
    result, html = _build_one(tmp_path, deck, strict=True)
    assert result.slide_count == 2
    assert (tmp_path / "out" / "slide_images" / "wide.svg").is_file()
    assert (tmp_path / "out" / "slide_images" / "tall.svg").is_file()
    assert 'src="slide_images/wide.svg"' in html
    assert "slide_images/tall.svg" in html.split('class="bg-layer"')[1].split(">")[0]
    # grid item flex-grow is each image's aspect over the row's summed aspect: read from
    # the SVGs' viewBox (4.0) and width/height (0.25)
    assert 'class="image-grid-item" style="flex: 0.9412 1 0"' in html
    assert 'class="image-grid-item" style="flex: 0.0588 1 0"' in html
