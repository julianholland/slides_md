"""Markdown body rendering: CommonMark + inline KaTeX, `.bullets` class injection."""

from __future__ import annotations

import re

from markdown_it import MarkdownIt

_UNSUPPORTED_BODY_RE = re.compile(r"(?m)^(#{1,6}\s|!\[)")


def _bullet_list_open(self, tokens, idx, options, env):  # noqa: ANN001
    token = tokens[idx]
    if token.level == 0:
        token.attrSet("class", "bullets")
    return self.renderToken(tokens, idx, options, env)


def _make_md() -> MarkdownIt:
    md = MarkdownIt("commonmark")
    md.add_render_rule("bullet_list_open", _bullet_list_open)
    return md


_MD = _make_md()


def check_unsupported_body_syntax(body: str) -> list[str]:
    """Warn on headings / markdown images in a slide body (use YAML fields instead)."""
    warnings = []
    if re.search(r"(?m)^#{1,6}\s", body):
        warnings.append("body contains a Markdown heading (#) — use the 'title'/'kicker' fields instead")
    if re.search(r"!\[[^\]]*\]\([^)]*\)", body):
        warnings.append("body contains a Markdown image (![]()) — use the 'image' field instead")
    return warnings


def render_body(body: str) -> str:
    """Render a slide body: paragraphs + up to 2 levels of bullets + inline formatting.

    Inline `$...$` / block `$$...$$` KaTeX delimiters are left untouched — they are
    rendered client-side by KaTeX's auto-render against the DOM text nodes.
    """
    if not body.strip():
        return ""
    return _MD.render(body)


def render_formula(formula: str) -> str:
    """Wrap a raw LaTeX string (no $$ delimiters) for client-side KaTeX rendering.

    Kept out of the CommonMark pipeline entirely: `_{...}` subscripts collide with
    CommonMark's underscore-emphasis flanking rules.
    """
    return f"$${formula}$$"
