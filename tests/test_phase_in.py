import pytest

from slide_maker.build import build
from slide_maker.parser import SlideMakerError
from slide_maker.phase_in import bullet_phase_classes, render_with_phase_tags


def _build(tmp_path, body_text, strict=False):
    src = tmp_path / "slides.md"
    src.write_text(body_text)
    out = tmp_path / "out"
    result = build(input_path=src, output_dir=out, strict=strict)
    html = (out / "index.html").read_text()
    return result, html


# --- unit tests: render_with_phase_tags / bullet_phase_classes -------------------

def test_top_level_phase_tags():
    html, target_count = render_with_phase_tags("- A\n  - A1\n- B\n- C\n", phase_level=1)
    assert target_count == 3
    assert '<li data-phase="0">A' in html
    assert '<li data-phase="1">B</li>' in html
    assert '<li data-phase="2">C</li>' in html
    # sub-bullet gets no tag of its own
    assert 'A1</li>' in html and '<li data-phase' not in html.split("A1")[0].split("A")[-1]


def test_sub_level_phase_tags_backfill_ancestor_and_fallback_leaf():
    # Section A has two level-2 children (Point 1, Point 2); Section B is a leaf at
    # level 1, shallower than target_depth=2, so it falls back to its own step.
    body = "- Section A\n  - Point 1\n  - Point 2\n- Section B\n"
    html, target_count = render_with_phase_tags(body, phase_level=2)
    assert target_count == 3
    # Section A backfills to Point 1's step (0), Point 2 is step 1, Section B is step 2
    assert '<li data-phase="0">Section A' in html
    assert '<li data-phase="0">Point 1</li>' in html
    assert '<li data-phase="1">Point 2</li>' in html
    assert '<li data-phase="2">Section B</li>' in html


def test_deep_phase_level_degrades_to_deepest_actual_leaf():
    # phase_level far deeper than anything in the body: falls back branch by branch.
    html, target_count = render_with_phase_tags("- A\n  - A1\n- B\n", phase_level=5)
    assert target_count == 2
    assert '<li data-phase="0">A' in html
    assert '<li data-phase="0">A1</li>' in html
    assert '<li data-phase="1">B</li>' in html


def test_bullet_phase_classes_dim_current_pending():
    html, _ = render_with_phase_tags("- A\n- B\n- C\n", phase_level=1)
    step1 = bullet_phase_classes(html, step=1, target_count=3)
    assert '<li data-phase="0" class="phase-dim">A</li>' in step1
    assert '<li data-phase="1">B</li>' in step1
    assert '<li data-phase="2" class="phase-pending">C</li>' in step1


def test_bullet_phase_classes_final_step_has_no_extra_classes():
    html, _ = render_with_phase_tags("- A\n- B\n", phase_level=1)
    final = bullet_phase_classes(html, step=2, target_count=2)
    assert 'class="phase-dim"' not in final
    assert 'class="phase-pending"' not in final


# --- end-to-end build tests --------------------------------------------------

PHASE_DECK = """\
---
layout: content
title: Rollout
phase_in: true
phase_images:
  - image: example-image-a
    alt: Step 1
  - image: example-image-b
    alt: Step 2
---

- First
- Second
- Third
"""


def test_expands_to_bullet_count_plus_one_physical_slides(tmp_path):
    result, html = _build(tmp_path, PHASE_DECK, strict=True)
    assert result.slide_count == 4  # 3 bullets + 1 final undim step
    assert html.count('<section class="slide') == 4


def test_shared_display_index_across_expanded_steps(tmp_path):
    _, html = _build(tmp_path, PHASE_DECK, strict=True)
    assert html.count('data-display-index="1"') == 4


def test_image_cycles_and_freezes_on_last(tmp_path):
    _, html = _build(tmp_path, PHASE_DECK, strict=True)
    assert html.count('src="slide_images/example-image-a.png"') == 1
    # steps 2, 3 (0-indexed 1, 2) and the final undim step all clamp to the last image
    assert html.count('src="slide_images/example-image-b.png"') == 3


def test_single_image_stays_static_across_all_steps(tmp_path):
    deck = """\
---
layout: content
title: Static
phase_in: true
phase_images:
  - image: example-image
    alt: Only one
---

- First
- Second
"""
    _, html = _build(tmp_path, deck, strict=True)
    assert html.count('src="slide_images/example-image.png"') == 3  # 2 bullets + 1 final step


def test_no_phase_images_leaves_media_col_empty(tmp_path):
    deck = """\
---
layout: content
title: Text only
phase_in: true
---

- First
- Second
"""
    _, html = _build(tmp_path, deck, strict=True)
    assert "<img" not in html.split('id="lightbox"')[0]


def test_ancestor_and_first_child_share_step_at_phase_level_2(tmp_path):
    deck = """\
---
layout: content
title: Nested
phase_in: true
phase_level: 2
---

- Section A
  - Point 1
  - Point 2
"""
    result, html = _build(tmp_path, deck, strict=True)
    assert result.slide_count == 3  # 2 targets + 1 final step
    sections = html.split('<section class="slide')
    step0 = sections[1]
    assert '<li data-phase="0">Section A' in step0
    assert '<li data-phase="0">Point 1</li>' in step0
    assert 'class="phase-pending"' in step0  # Point 2 still pending


def test_counter_stays_on_one_number_then_advances(tmp_path):
    deck = PHASE_DECK + "\n+++\n\n---\nlayout: title\ntitle: End\n---\n"
    _, html = _build(tmp_path, deck, strict=True)
    assert html.count('data-display-index="1"') == 4
    assert html.count('data-display-index="2"') == 1


# --- validation errors --------------------------------------------------

def test_phase_in_rejected_on_non_content_layout(tmp_path):
    deck = "---\nlayout: stacked\ntitle: X\nphase_in: true\n---\n\n- A\n"
    with pytest.raises(SlideMakerError, match="phase_in is only used by layout 'content'"):
        _build(tmp_path, deck)


def test_phase_in_rejected_with_other_media_fields(tmp_path):
    deck = "---\nlayout: content\ntitle: X\nphase_in: true\nimage: example-image\n---\n\n- A\n"
    with pytest.raises(SlideMakerError, match="may only set one of"):
        _build(tmp_path, deck)


def test_phase_in_requires_at_least_one_bullet(tmp_path):
    deck = "---\nlayout: content\ntitle: X\nphase_in: true\n---\n\nJust a paragraph, no bullets.\n"
    with pytest.raises(SlideMakerError, match="requires at least one bullet point"):
        _build(tmp_path, deck)


def test_phase_images_rejected_without_phase_in(tmp_path):
    deck = (
        "---\nlayout: content\ntitle: X\n"
        "phase_images:\n  - image: example-image\n---\n\nsome text\n"
    )
    with pytest.raises(SlideMakerError, match="phase_images set without phase_in"):
        _build(tmp_path, deck)


def test_phase_level_rejected_without_phase_in(tmp_path):
    deck = "---\nlayout: content\ntitle: X\nphase_level: 2\n---\n\nsome text\n"
    with pytest.raises(SlideMakerError, match="phase_level set without phase_in"):
        _build(tmp_path, deck)


def test_phase_level_must_be_positive_int(tmp_path):
    deck = "---\nlayout: content\ntitle: X\nphase_in: true\nphase_level: 0\n---\n\n- A\n"
    with pytest.raises(SlideMakerError, match="phase_level must be an integer >= 1"):
        _build(tmp_path, deck)
