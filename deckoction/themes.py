"""Named theme presets: colors, a body font, and an optional watermark image.

`deck.yaml`'s `theme:` field can name one of `THEME_PRESETS` (e.g. `theme: alomancy`) to switch
every slide's colors/font/watermark in a single line, or still be a raw dict of CSS custom-
property overrides (the pre-existing, backward-compatible form — see `schema.build_deck_config`).

To add a new preset, register a `ThemeDefinition` here (or from any code that imports this module
before a deck is built) via `register_theme`; no other file needs to change.
"""

from __future__ import annotations

from dataclasses import dataclass

# CSS custom-property names style.css/base.html.jinja already consume for slide colors.
COLOR_KEYS = (
    "bg", "bg-panel", "fg", "fg-muted", "accent", "accent-dim", "border",
    "title-fg", "title-transform", "panel-fg", "equation-bg", "equation-fg",
)


@dataclass
class ThemeDefinition:
    name: str
    colors: dict[str, str]
    font_body: str
    watermark: str | None = None
    watermark_opacity: float = 0.12
    watermark_size: float = 0.08


THEME_PRESETS: dict[str, ThemeDefinition] = {}


def register_theme(theme: ThemeDefinition) -> None:
    THEME_PRESETS[theme.name] = theme


register_theme(
    ThemeDefinition(
        name="default",
        colors={
            "bg": "#1a1d23",
            "bg-panel": "#22262e",
            "fg": "#eef0f3",
            "fg-muted": "#aab1bd",
            "accent": "#f4c542",
            "accent-dim": "#8a7228",
            "border": "#3a3f4a",
        },
        font_body='"Segoe UI", "Helvetica Neue", Arial, sans-serif',
        watermark=None,
    )
)

register_theme(
    ThemeDefinition(
        name="alomancy",
        colors={
            "bg": "#1a1424",
            "bg-panel": "#241b30",
            "fg": "#f0ecf7",
            "fg-muted": "#b3a8c2",
            "accent": "#6C2FBE",  # ALOMANCY_PURPLE, brand primary
            "accent-dim": "#3A106E",  # STAGE2_COLOR, "darkened brand violet"
            "border": "#374151",  # DIAGONAL_COLOR, dark charcoal
        },
        font_body='"Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif',
        watermark="themes/alomancy/watermark.png",
        watermark_opacity=0.12,
        watermark_size=0.08,
    )
)

register_theme(
    ThemeDefinition(
        name="neuefische",
        colors={
            "bg": "#14012c",
            "bg-panel": "#440293",
            "fg": "#feede8",
            "fg-muted": "#fbb5a2",
            "accent": "#f44717",  # Neuefische orange, brand primary
            "accent-dim": "#922b0e",  # STAGE2_COLOR, "darkened brand violet"
            "border": "#07000f",  # DIAGONAL_COLOR, dark charcoal
        },
        font_body='"Poppins", "Nunito Sans", "Segoe UI", "Helvetica Neue", Arial, sans-serif',
        watermark="themes/neuefische/watermark.png",
        watermark_opacity=0.08,
        watermark_size=0.05,
    )
)

register_theme(
    ThemeDefinition(
        name="fhi",
        colors={
            "bg":"#eef0f3",
            "bg-panel": "#005555",
            # darker than bg-panel deliberately, not matching it.
            "fg": "#29485d",
            "fg-muted": "#29485d",
            "accent": "#29485d",
            "accent-dim": "#172833",
            "border": "#29485d",
            "title-fg": "#ffffff",  # title slide's h1/subtitle/date sit on a dark translucent
                                    # panel regardless of theme -- white keeps them legible there
            "title-transform": "uppercase",
            # blockquotes/code/formula-box/placeholders sit on a --bg-panel background;
            # fg-muted (#29485d) is too close to bg-panel (#005555) to read there, so
            # this needs its own white override, same reasoning as title-fg above.
            "panel-fg": "#ffffff",
        },
        font_body='Arial, "Helvetica Neue", "Segoe UI", sans-serif',
        watermark="themes/fhi/fhi_watermark.png",
        watermark_opacity=0.08,
        watermark_size=0.05,
    )
)