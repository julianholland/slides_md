from slide_maker.render import check_unsupported_body_syntax, render_body, render_formula


def test_only_top_level_ul_gets_bullets_class():
    html = render_body("- top\n  - nested\n- top2\n")
    assert html.count('class="bullets"') == 1
    assert html.startswith('<ul class="bullets">')
    assert "<ul>\n<li>nested" in html


def test_inline_math_passes_through_unescaped():
    html = render_body("Rate is $S(q)$ over time.\n")
    assert "$S(q)$" in html


def test_formula_field_untouched_by_markdown_renderer():
    # underscores in `_{...}` must not be mangled by CommonMark emphasis parsing
    wrapped = render_formula(r"E = \int_{q_{min}}^{q_{max}} S(q)\, dq")
    assert wrapped == r"$$E = \int_{q_{min}}^{q_{max}} S(q)\, dq$$"


def test_empty_body_renders_empty():
    assert render_body("") == ""
    assert render_body("   \n") == ""


def test_warns_on_heading_in_body():
    warnings = check_unsupported_body_syntax("# A heading\n\n- bullet\n")
    assert any("heading" in w for w in warnings)


def test_warns_on_markdown_image_in_body():
    warnings = check_unsupported_body_syntax("![alt](foo.png)\n")
    assert any("image" in w for w in warnings)


def test_no_warnings_for_plain_body():
    assert check_unsupported_body_syntax("- a\n  - b\n") == []


def test_blockquote_renders_and_is_not_warned_on():
    html = render_body("> A quoted callout\n")
    assert html == "<blockquote>\n<p>A quoted callout</p>\n</blockquote>\n"
    assert check_unsupported_body_syntax("> A quoted callout\n") == []
