from pathlib import Path

import pytest

from slide_maker.parser import SlideMakerError, parse_slides_file, strip_comments


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


def test_strip_comments_basic():
    assert strip_comments("before <!-- hidden --> after") == "before  after"


def test_strip_comments_triple_dash_variant():
    assert strip_comments("before <!--- hidden ---> after") == "before  after"


def test_strip_comments_multiline():
    text = "before\n<!--\nall of\nthis is hidden\n-->\nafter"
    assert strip_comments(text) == "before\n\nafter"


def test_strip_comments_multiple_blocks():
    text = "a <!-- one --> b <!-- two --> c"
    assert strip_comments(text) == "a  b  c"


def test_comment_in_slide_body_is_removed(tmp_path):
    path = write(
        tmp_path,
        "---\nlayout: content\ntitle: A\n---\nvisible text\n<!-- hidden bullet -->\nmore visible text\n",
    )
    slides = parse_slides_file(path)
    assert len(slides) == 1
    assert "hidden bullet" not in slides[0].body
    assert "visible text" in slides[0].body
    assert "more visible text" in slides[0].body


def test_commented_out_slide_is_never_parsed(tmp_path):
    path = write(
        tmp_path,
        "---\nlayout: content\ntitle: A\n---\nbody a\n"
        "+++\n"
        "<!--\n"
        "+++\n"
        "---\nlayout: content\ntitle: Draft, not ready\n---\nbody b\n"
        "-->\n"
        "+++\n"
        "---\nlayout: content\ntitle: C\n---\nbody c\n",
    )
    slides = parse_slides_file(path)
    assert len(slides) == 2
    assert [s.frontmatter["title"] for s in slides] == ["A", "C"]


def test_comment_in_frontmatter_is_removed(tmp_path):
    path = write(
        tmp_path,
        "---\nlayout: content\ntitle: A\n<!-- kicker: Draft -->\n---\nbody\n",
    )
    slides = parse_slides_file(path)
    assert len(slides) == 1
    assert "kicker" not in slides[0].frontmatter
