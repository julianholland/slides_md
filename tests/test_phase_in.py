import pytest

from deckoction.build import build
from deckoction.parser import SlideMakerError
from deckoction.phase_in import bullet_phase_classes, render_with_phase_tags


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


# --- other layouts: stacked / split / image ------------------------------

def _sections(html):
    return html.split('<section class="slide')[1:]


def test_stacked_phase_in_reveals_bullets_and_keeps_formula(tmp_path):
    deck = (
        "---\nlayout: stacked\ntitle: S\nphase_in: true\nformula: E = mc^2\n---\n\n"
        "- A\n- B\n"
    )
    result, html = _build(tmp_path, deck, strict=True)
    assert result.slide_count == 3
    sections = _sections(html)
    assert all('class="formula-box"' in sec for sec in sections)
    assert '<li data-phase="1" class="phase-pending">B</li>' in sections[0]
    assert '<li data-phase="0" class="phase-dim">A</li>' in sections[1]
    assert "phase-dim" not in sections[2] and "phase-pending" not in sections[2]


def test_split_phase_in_reveals_one_panel_per_step(tmp_path):
    deck = (
        "---\nlayout: split\ntitle: P\nphase_in: true\npanels:\n"
        "  - image: example-image-a\n  - image: example-image-b\n  - image: example-image-c\n---\n"
    )
    result, html = _build(tmp_path, deck, strict=True)
    assert result.slide_count == 4
    sections = _sections(html)
    assert all('data-display-index="1"' in sec for sec in sections)

    def panel_classes(sec):
        return [chunk.split('"')[0] for chunk in sec.split('<div class="panel')[1:] if chunk.startswith((" ", '"'))]

    assert panel_classes(sections[0]) == ["", " phase-pending", " phase-pending"]
    assert panel_classes(sections[1]) == [" phase-dim", "", " phase-pending"]
    assert panel_classes(sections[2]) == [" phase-dim", " phase-dim", ""]
    assert panel_classes(sections[3]) == ["", "", ""]


def test_image_phase_in_cycles_images_without_final_step(tmp_path):
    deck = (
        "---\nlayout: image\ntitle: I\nphase_in: true\nphase_images:\n"
        "  - image: example-image-a\n  - image: example-image-b\n  - image: example-image-c\n---\n"
    )
    result, html = _build(tmp_path, deck, strict=True)
    assert result.slide_count == 3
    sections = _sections(html)
    for sec, letter in zip(sections, "abc"):
        assert f"slide_images/example-image-{letter}.png" in sec
        assert 'data-display-index="1"' in sec
        assert 'aria-label="Placeholder image ' + letter.upper() + '"' in sec


# --- validation errors --------------------------------------------------

def test_phase_in_rejected_on_title_layout(tmp_path):
    deck = "---\nlayout: title\ntitle: X\nphase_in: true\n---\n"
    with pytest.raises(SlideMakerError, match="phase_in is only used by layouts"):
        _build(tmp_path, deck)


def test_phase_level_rejected_on_split(tmp_path):
    deck = "---\nlayout: split\nphase_in: true\nphase_level: 2\npanels:\n  - image: example-image\n---\n"
    with pytest.raises(SlideMakerError, match="phase_level is only used by layouts"):
        _build(tmp_path, deck)


@pytest.mark.parametrize(
    "layout_fields",
    ["layout: stacked\ntitle: X", "layout: split\npanels:\n  - image: example-image"],
)
def test_phase_images_rejected_on_stacked_and_split(tmp_path, layout_fields):
    deck = f"---\n{layout_fields}\nphase_in: true\nphase_images:\n  - image: example-image\n---\n\n- A\n"
    with pytest.raises(SlideMakerError, match="phase_images is only used by layouts"):
        _build(tmp_path, deck)


def test_image_phase_in_rejects_image_field(tmp_path):
    deck = (
        "---\nlayout: image\nimage: example-image\nphase_in: true\n"
        "phase_images:\n  - image: example-image-a\n---\n"
    )
    with pytest.raises(SlideMakerError, match="remove 'image'"):
        _build(tmp_path, deck)


def test_image_phase_in_requires_phase_images(tmp_path):
    deck = "---\nlayout: image\nphase_in: true\n---\n"
    with pytest.raises(SlideMakerError, match="requires a non-empty 'phase_images'"):
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


# --- phase_images entries holding an `images` pair -----------------------------

PAIR_DECK = """\
---
layout: content
title: Pairs
phase_in: true
phase_images:
  - image: example-image-a
    alt: Single
  - images:
    - image: example-image-b
      alt: Left
    - image: example-image-c
      alt: Right
---

- First
- Second
"""


def test_phase_images_entry_can_be_an_image_pair(tmp_path):
    result, html = _build(tmp_path, PAIR_DECK, strict=True)
    assert result.slide_count == 3
    first, second, final = _sections(html)
    assert "example-image-a.png" in first and "image-grid" not in first
    for sec in (second, final):  # step 2 and the final step clamp to the pair
        assert 'class="image-grid"' in sec
        assert 'src="slide_images/example-image-b.png"' in sec
        assert 'src="slide_images/example-image-c.png"' in sec
        assert "example-image-a.png" not in sec


def test_phase_images_group_needs_at_least_two(tmp_path):
    deck = PAIR_DECK.replace("    - image: example-image-c\n      alt: Right\n", "")
    with pytest.raises(SlideMakerError, match=r"phase_images\[1\]\.images needs at least 2"):
        _build(tmp_path, deck)


def test_phase_images_group_of_three(tmp_path):
    deck = PAIR_DECK.replace(
        "    - image: example-image-c\n      alt: Right\n",
        "    - image: example-image-c\n      alt: Right\n    - image: example-image-d\n      alt: Extra\n",
    )
    _, html = _build(tmp_path, deck, strict=True)
    second = _sections(html)[1]
    assert second.count('class="image-grid-item"') == 3


def test_phase_images_pair_rejected_on_image_layout(tmp_path):
    deck = (
        "---\nlayout: image\nphase_in: true\nphase_images:\n"
        "  - images:\n    - image: example-image-a\n    - image: example-image-b\n---\n"
    )
    with pytest.raises(SlideMakerError, match="only supported on layout 'content'"):
        _build(tmp_path, deck)


def test_phase_images_entry_without_image_is_a_clear_error(tmp_path):
    deck = "---\nlayout: content\ntitle: X\nphase_in: true\nphase_images:\n  - alt: oops\n---\n\n- A\n"
    with pytest.raises(SlideMakerError, match=r"phase_images\[0\] must be a mapping with an 'image' field"):
        _build(tmp_path, deck)


EQUATION_DECK = """---
layout: content
title: Eq
phase_in: true
phase_images:
  - equation: $a^2+b^2=c^2$
  - image: example-image-a
---

- First
- Second
"""


def test_phase_images_equation_step_then_image(tmp_path):
    result, html = _build(tmp_path, EQUATION_DECK, strict=True)
    assert result.slide_count == 3
    first, second, final = _sections(html)
    assert '<div class="media-equation">$$a^2+b^2=c^2$$</div>' in first
    assert "<img" not in first.split('class="media-col"')[1]
    for sec in (second, final):
        assert "media-equation" not in sec
        assert 'src="slide_images/example-image-a.png"' in sec


def test_phase_images_equation_rejected_on_image_layout(tmp_path):
    deck = "---\nlayout: image\nphase_in: true\nphase_images:\n  - equation: a\n---\n"
    with pytest.raises(SlideMakerError, match="'equation' step is only supported on layout 'content'"):
        _build(tmp_path, deck)


def test_phase_images_equation_and_image_in_one_entry_rejected(tmp_path):
    deck = EQUATION_DECK.replace("  - equation: $a^2+b^2=c^2$\n", "  - equation: a\n    image: example-image-b\n")
    with pytest.raises(SlideMakerError, match="may set 'equation' or 'image'/'images', not both"):
        _build(tmp_path, deck)
