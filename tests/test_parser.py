from pathlib import Path

import pytest

from slide_maker.parser import SlideMakerError, parse_slides_file


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "slides.md"
    p.write_text(text)
    return p


def test_splits_on_plus_separator(tmp_path):
    path = write(
        tmp_path,
        "---\nlayout: title\ntitle: A\n---\nbody a\n"
        "+++\n"
        "---\nlayout: content\ntitle: B\n---\nbody b\n",
    )
    slides = parse_slides_file(path)
    assert len(slides) == 2
    assert slides[0].frontmatter["title"] == "A"
    assert slides[0].body == "body a"
    assert slides[1].frontmatter["title"] == "B"
    assert slides[1].body == "body b"


def test_tolerates_leading_and_trailing_separator(tmp_path):
    path = write(
        tmp_path,
        "+++\n---\nlayout: content\ntitle: A\n---\nbody\n+++\n",
    )
    slides = parse_slides_file(path)
    assert len(slides) == 1
    assert slides[0].frontmatter["title"] == "A"


def test_tolerates_crlf(tmp_path):
    path = write(
        tmp_path,
        "---\r\nlayout: content\r\ntitle: A\r\n---\r\nbody\r\n",
    )
    slides = parse_slides_file(path)
    assert len(slides) == 1
    assert slides[0].frontmatter["title"] == "A"


def test_missing_frontmatter_raises_with_slide_index(tmp_path):
    path = write(tmp_path, "just some text, no frontmatter\n")
    with pytest.raises(SlideMakerError) as exc:
        parse_slides_file(path)
    assert "slide 1" in str(exc.value)


def test_invalid_yaml_raises_with_slide_index(tmp_path):
    path = write(
        tmp_path,
        "---\nlayout: content\ntitle: [unclosed\n---\nbody\n"
        "+++\n"
        "---\nlayout: content\ntitle: fine\n---\nbody\n",
    )
    with pytest.raises(SlideMakerError) as exc:
        parse_slides_file(path)
    assert "slide 1" in str(exc.value)


def test_empty_file_raises(tmp_path):
    path = write(tmp_path, "\n\n")
    with pytest.raises(SlideMakerError):
        parse_slides_file(path)
