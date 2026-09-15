"""Layout -> Jinja template mapping."""

from __future__ import annotations

TEMPLATE_BY_LAYOUT = {
    "title": "slide_title.html.jinja",
    "content": "slide_content.html.jinja",
    "stacked": "slide_stacked.html.jinja",
    "split": "slide_split.html.jinja",
    "image": "slide_image.html.jinja",
    "references": "slide_references.html.jinja",
}


def template_for(layout: str) -> str:
    return TEMPLATE_BY_LAYOUT[layout]
