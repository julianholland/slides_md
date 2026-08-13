from pathlib import Path

import pytest

from slide_maker.build import build
from slide_maker.parser import SlideMakerError

MINIMAL_SLIDES = "---\nlayout: title\ntitle: Test Deck\n---\n"


def _build(tmp_path, deck_yaml_text=None):
    src = tmp_path / "slides.md"
    src.write_text(MINIMAL_SLIDES)
    config_path = None
    if deck_yaml_text is not None:
        config_path = tmp_path / "deck.yaml"
        config_path.write_text(deck_yaml_text)
    out = tmp_path / "out"
    build(input_path=src, output_dir=out, config_path=config_path)
    return out


def test_no_theme_key_emits_no_style_block_or_watermark(tmp_path):
    # No theme: at all -> byte-for-byte the same as before theming existed.
    out = _build(tmp_path)
    html = (out / "index.html").read_text()
    assert "<style>" not in html
    assert "theme-watermark" not in html
    assert not (out / "assets" / "theme-watermark.png").exists()


def test_alomancy_preset_sets_colors_font_and_watermark(tmp_path):
    out = _build(tmp_path, "title: Test\ntheme: alomancy\n")
    html = (out / "index.html").read_text()

    assert "--accent: #6C2FBE;" in html
    assert "--accent-dim: #3A106E;" in html
    assert '--font-body: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;' in html
    assert '<img class="theme-watermark" src="assets/themes/alomancy/watermark.png"' in html
    assert (out / "assets" / "themes" / "alomancy" / "watermark.png").exists()


def test_default_preset_matches_undecorated_style_css_values(tmp_path):
    # Explicit theme: default should resolve to the exact same 7 values that
    # style.css's own :root block already has -- a visual no-op, just opted in.
    out = _build(tmp_path, "title: Test\ntheme: default\n")
    html = (out / "index.html").read_text()
    css = (out / "assets" / "style.css").read_text()

    for key in ("bg", "bg-panel", "fg", "fg-muted", "accent", "accent-dim", "border"):
        css_value = css.split(f"--{key}:")[1].split(";")[0].strip()
        assert f"--{key}: {css_value};" in html
    assert "theme-watermark" not in html


def test_raw_dict_theme_is_backward_compatible(tmp_path):
    # The pre-existing free-form override form must keep working exactly as
    # before: only the overridden key is emitted, nothing merged from a preset.
    out = _build(tmp_path, 'title: Test\ntheme:\n  accent: "#4cc9f0"\n')
    html = (out / "index.html").read_text()
    assert "--accent: #4cc9f0;" in html
    assert "--bg:" not in html
    assert "--font-body" not in html
    assert "theme-watermark" not in html


def test_unknown_theme_name_raises_with_available_list(tmp_path):
    src = tmp_path / "slides.md"
    src.write_text(MINIMAL_SLIDES)
    config_path = tmp_path / "deck.yaml"
    config_path.write_text("theme: nonexistent\n")
    with pytest.raises(SlideMakerError, match="unknown theme 'nonexistent'.*alomancy.*default|unknown theme"):
        build(input_path=src, output_dir=tmp_path / "out", config_path=config_path)


def test_unsafe_raw_theme_value_rejected(tmp_path):
    # A value containing '}' could break out of the :root{...} rule / <style>
    # block it's rendered into verbatim -- must be rejected, not escaped (HTML
    # entities aren't decoded inside <style>, a "raw text" element).
    src = tmp_path / "slides.md"
    src.write_text(MINIMAL_SLIDES)
    config_path = tmp_path / "deck.yaml"
    config_path.write_text('theme:\n  accent: "red; } body { display:none"\n')
    with pytest.raises(SlideMakerError, match="theme override"):
        build(input_path=src, output_dir=tmp_path / "out", config_path=config_path)


def test_watermark_src_is_inline_not_css_custom_property(tmp_path):
    # Mirrors test_background_image_uses_inline_style_not_css_custom_property:
    # a url() inside a CSS custom property resolves relative to the stylesheet
    # consuming it via var() (assets/style.css), not index.html, so the
    # watermark path must be a literal inline attribute, never routed through
    # var(--something) in style.css.
    out = _build(tmp_path, "title: Test\ntheme: alomancy\n")
    css = (out / "assets" / "style.css").read_text()
    watermark_rule = css[css.index(".theme-watermark {"):css.index("}", css.index(".theme-watermark {"))]
    assert "url(" not in watermark_rule
    html = (out / "index.html").read_text()
    assert 'src="assets/themes/alomancy/watermark.png"' in html
