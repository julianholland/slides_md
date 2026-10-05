import pytest

from slide_maker.build import build
from slide_maker.parser import SlideMakerError
from slide_maker.references import find_citations, format_acs, parse_bibtex, parse_plain

BIB = """\
@article{smith2020,
  author = {Smith, John A. and Doe, Jane B.},
  title = {A Study of {DNA} Nanotechnology},
  journal = {Journal of Chemistry},
  year = {2020},
  volume = {12},
  pages = {34--56},
  doi = {10.1021/xyz123}
}

@book{jones2019,
  author = {Jones, Albert},
  title = {Principles of Organic Synthesis},
  publisher = {Academic Press},
  address = {New York},
  year = {2019}
}
"""

PLAIN = """\
"smith2020": "Smith, J. A. et al. A pasted-as-is citation." : "10.1021/xyz123"
"jones2019": "Jones, A. Another citation with a \\"quoted\\" word, no DOI."
"""


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return path


def _build(tmp_path, slides_text, bib_text, bib_name="refs.bib", strict=True):
    slides = _write(tmp_path, "slides.md", slides_text)
    _write(tmp_path, bib_name, bib_text)
    config = _write(tmp_path, "deck.yaml", f"bibliography: {bib_name}\n")
    out = tmp_path / "out"
    result = build(input_path=slides, output_dir=out, config_path=config, strict=strict)
    html = (out / "index.html").read_text()
    return result, html


# --- BibTeX parsing -----------------------------------------------------------------

def test_parse_bibtex_article_acs_format():
    refs = parse_bibtex(BIB)
    assert refs["smith2020"].html == (
        "Smith, J. A.; Doe, J. B. A Study of DNA Nanotechnology. "
        "<i>Journal of Chemistry</i> <b>2020</b>, <i>12</i>, 34–56."
    )
    assert refs["smith2020"].doi_url == "https://doi.org/10.1021/xyz123"


def test_parse_bibtex_book_acs_format():
    refs = parse_bibtex(BIB)
    assert refs["jones2019"].html == "Jones, A. Principles of Organic Synthesis. Academic Press: New York, <b>2019</b>."
    assert refs["jones2019"].doi_url is None


def test_author_initials_from_first_last_form():
    fields = {"author": "John Allen Smith", "year": "2021"}
    assert format_acs("misc", fields).startswith("Smith, J. A.")


def test_missing_optional_fields_degrade_gracefully():
    fields = {"author": "Smith, J.", "title": "A Title"}
    result = format_acs("article", fields)
    assert result == "Smith, J. A Title."


def test_unbalanced_braces_do_not_crash():
    # No closing brace at all -- the entry-splitter must still terminate.
    refs = parse_bibtex("@article{k,\n  author = {Smith, J.\n")
    assert "k" in refs


# --- Plain format ---------------------------------------------------------------

def test_parse_plain_two_and_three_field_lines():
    refs = parse_plain(PLAIN, "refs.md")
    assert refs["smith2020"].html == "Smith, J. A. et al. A pasted-as-is citation."
    assert refs["smith2020"].doi_url == "https://doi.org/10.1021/xyz123"
    assert refs["jones2019"].html == 'Jones, A. Another citation with a "quoted" word, no DOI.'
    assert refs["jones2019"].doi_url is None


def test_parse_plain_malformed_line_raises_with_line_number():
    with pytest.raises(SlideMakerError, match="refs.md:2"):
        parse_plain('"good": "fine"\nnot a valid line\n', "refs.md")


# --- find_citations ---------------------------------------------------------------

def test_find_citations_single_and_multi():
    assert find_citations("a [@k1] b [@k1; @k2] c") == [["k1"], ["k1", "k2"]]


# --- end-to-end numbering / substitution / footnotes / badges ----------------------

DECK = """\
---
layout: content
title: Intro
image: example-image
image_alt: A diagram
image_reference: jones2019
---

Body text cites [@smith2020] then again [@smith2020; @jones2019].

+++

---
layout: references
title: References
---
"""


def test_global_numbering_body_before_image_field(tmp_path):
    _, html = _build(tmp_path, DECK, BIB)
    # smith2020 cited first in body text -> 1; jones2019 first seen later in the
    # same body citation, before the image_reference field is processed -> 2.
    assert 'class="citation-badge">2' in html
    assert "1. Smith, J. A." in html
    assert "2. Jones, A." in html


def test_repeated_citation_reuses_same_number(tmp_path):
    _, html = _build(tmp_path, DECK, BIB)
    assert html.count(">1</a>") + html.count(">1<") >= 2  # cited twice


def test_body_substitution_produces_sup_and_doi_link(tmp_path):
    _, html = _build(tmp_path, DECK, BIB)
    assert '<sup class="citation">[<a href="https://doi.org/10.1021/xyz123"' in html
    # smith2020 (1) has a DOI and links; jones2019 (2) doesn't and stays a bare number
    assert html.count('rel="noopener">1</a>,2]</sup>') == 1


def test_image_badge_and_footnote_present(tmp_path):
    _, html = _build(tmp_path, DECK, BIB)
    assert '<span class="citation-badge">2</span>' in html
    assert '<div class="citation-footnotes">' in html


def test_references_slide_lists_full_ordered_bibliography(tmp_path):
    _, html = _build(tmp_path, DECK, BIB)
    assert '<span class="ref-num">1.</span>' in html
    assert '<span class="ref-num">2.</span>' in html


def test_bibtex_dna_braces_stripped(tmp_path):
    _, html = _build(tmp_path, DECK, BIB)
    assert "A Study of DNA Nanotechnology" in html
    assert "{DNA}" not in html


# --- validation errors --------------------------------------------------

def test_unknown_citation_key_is_fatal(tmp_path):
    deck = "---\nlayout: stacked\ntitle: X\n---\n\nCiting [@nope].\n"
    with pytest.raises(SlideMakerError, match="unknown citation key 'nope'"):
        _build(tmp_path, deck, BIB)


def test_citation_with_no_bibliography_configured_is_fatal(tmp_path):
    slides = _write(tmp_path, "slides.md", "---\nlayout: stacked\ntitle: X\n---\n\nCiting [@nope].\n")
    with pytest.raises(SlideMakerError, match="unknown citation key"):
        build(input_path=slides, output_dir=tmp_path / "out")


def test_missing_bibliography_file_is_fatal(tmp_path):
    slides = _write(tmp_path, "slides.md", "---\nlayout: title\ntitle: X\n---\n")
    config = _write(tmp_path, "deck.yaml", "bibliography: does-not-exist.bib\n")
    with pytest.raises(SlideMakerError, match="bibliography file not found"):
        build(input_path=slides, output_dir=tmp_path / "out", config_path=config)


def test_deck_with_no_citations_is_unaffected_by_unconfigured_bibliography(tmp_path):
    # No `bibliography:` at all, and nothing cited -- fully inert, builds fine.
    slides = _write(tmp_path, "slides.md", "---\nlayout: title\ntitle: X\n---\n")
    result = build(input_path=slides, output_dir=tmp_path / "out")
    assert result.warnings == []


# --- phase-in interaction --------------------------------------------------------

def _footnotes_per_physical_slide(html):
    import re

    sections = html.split('<section class="slide')[1:]
    return [re.findall(r'citation-footnote-entry">([^<]*)', s) for s in sections]


def test_phase_in_slide_shows_only_current_steps_footnotes(tmp_path):
    deck = """\
---
layout: content
title: Rollout
phase_in: true
---

- First point [@smith2020]
- Second point [@jones2019]
"""
    result, html = _build(tmp_path, deck, BIB)
    assert result.slide_count == 3  # 2 bullets + 1 final step
    footnotes = _footnotes_per_physical_slide(html)
    assert len(footnotes[0]) == 1 and footnotes[0][0].startswith("1. Smith")
    assert len(footnotes[1]) == 1 and footnotes[1][0].startswith("2. Jones")


def test_phase_in_final_step_shows_union_of_all_footnotes(tmp_path):
    deck = """\
---
layout: content
title: Rollout
phase_in: true
---

- First point [@smith2020]
- Second point [@jones2019]
"""
    _, html = _build(tmp_path, deck, BIB)
    footnotes = _footnotes_per_physical_slide(html)
    final = footnotes[2]
    assert len(final) == 2
    assert final[0].startswith("1. Smith")
    assert final[1].startswith("2. Jones")


def test_phase_in_ancestor_citation_and_first_child_share_step(tmp_path):
    deck = """\
---
layout: content
title: Nested
phase_in: true
phase_level: 2
---

- Section A [@smith2020]
  - Point 1
  - Point 2 [@jones2019]
"""
    result, html = _build(tmp_path, deck, BIB)
    assert result.slide_count == 3  # 2 targets + 1 final step
    footnotes = _footnotes_per_physical_slide(html)
    # step 0: "Section A" (backfilled to Point 1's step) cites smith2020
    assert len(footnotes[0]) == 1 and footnotes[0][0].startswith("1. Smith")
    # step 1: "Point 2" is current, cites jones2019 only
    assert len(footnotes[1]) == 1 and footnotes[1][0].startswith("2. Jones")
    # final step: union of both
    assert len(footnotes[2]) == 2


def test_phase_in_image_reference_shown_only_on_its_own_steps(tmp_path):
    deck = """\
---
layout: content
title: Rollout
phase_in: true
phase_images:
  - image: example-image-a
    reference: smith2020
  - image: example-image-b
    reference: jones2019
---

- First point
- Second point
- Third point
"""
    _, html = _build(tmp_path, deck, BIB)
    footnotes = _footnotes_per_physical_slide(html)
    # 3 bullets -> steps 0,1,2 real, step 3 final; images clamp: step0->img0(smith),
    # steps 1-3 -> img1 (jones, last entry, frozen)
    assert len(footnotes[0]) == 1 and footnotes[0][0].startswith("1. Smith")
    assert len(footnotes[1]) == 1 and footnotes[1][0].startswith("2. Jones")
    assert len(footnotes[2]) == 1 and footnotes[2][0].startswith("2. Jones")
    final = footnotes[3]
    assert len(final) == 2
