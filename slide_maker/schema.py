"""Per-slide and deck-wide config validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_cls

from .parser import RawSlide, SlideMakerError

VALID_LAYOUTS = {"title", "content", "stacked", "split", "image"}
VALID_FITS = {"cover", "contain"}

KNOWN_FIELDS = {
    "layout", "title", "kicker", "subtitle", "author", "date",
    "image", "image_alt", "image_label", "images", "video", "panels", "background",
    "background_opacity", "fit", "formula", "formula_note", "notes", "id", "classes",
}


@dataclass
class Panel:
    image: str
    label: str = ""
    alt: str = ""


@dataclass
class SlideConfig:
    index: int
    layout: str = "content"
    title: str | None = None
    kicker: str | None = None
    subtitle: str | None = None
    author: str | None = None
    date: str | None = None
    image: str | None = None
    image_alt: str = ""
    image_label: str | None = None
    images: list[Panel] = field(default_factory=list)
    video: str | None = None
    panels: list[Panel] = field(default_factory=list)
    background: str | None = None
    background_opacity: float = 1.0
    fit: str = "contain"
    formula: str | None = None
    formula_note: str | None = None
    notes: str | None = None
    id: str = ""
    classes: str = ""
    body: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class DeckConfig:
    page_title: str = "Slides"
    default_author: str | None = None
    theme: dict = field(default_factory=dict)


def build_deck_config(raw: dict) -> DeckConfig:
    return DeckConfig(
        page_title=raw.get("title", "Slides"),
        default_author=raw.get("default_author"),
        theme=raw.get("theme") or {},
    )


def _check_opacity(fm: dict, idx: int, strict: bool, warnings: list[str]) -> float:
    opacity = fm.get("background_opacity", 1.0)
    try:
        opacity = float(opacity)
    except (TypeError, ValueError):
        raise SlideMakerError("background_opacity must be a number", slide_index=idx) from None
    if not 0.0 <= opacity <= 1.0:
        raise SlideMakerError("background_opacity must be between 0 and 1", slide_index=idx)
    fills_slide = fm.get("background") or (fm.get("layout") == "image" and fm.get("image"))
    if "background_opacity" in fm and not fills_slide:
        msg = "background_opacity set without a background image"
        if strict:
            raise SlideMakerError(msg, slide_index=idx)
        warnings.append(msg)
    return opacity


def validate_slide(raw_slide: RawSlide, deck: DeckConfig, strict: bool) -> SlideConfig:
    fm = raw_slide.frontmatter
    idx = raw_slide.index
    warnings: list[str] = []

    unknown = set(fm) - KNOWN_FIELDS
    if unknown:
        msg = f"unknown frontmatter field(s): {', '.join(sorted(unknown))}"
        if strict:
            raise SlideMakerError(msg, slide_index=idx)
        warnings.append(msg)

    layout = fm.get("layout", "content")
    if layout not in VALID_LAYOUTS:
        raise SlideMakerError(
            f"invalid layout '{layout}' (must be one of {sorted(VALID_LAYOUTS)})",
            slide_index=idx,
        )

    panels = [
        Panel(image=p["image"], label=p.get("label", ""), alt=p.get("alt", ""))
        for p in (fm.get("panels") or [])
    ]

    images = [
        Panel(image=im["image"], label=im.get("label", ""), alt=im.get("alt", ""))
        for im in (fm.get("images") or [])
    ]

    opacity = _check_opacity(fm, idx, strict, warnings)

    fit = fm.get("fit", "contain")
    if fit not in VALID_FITS:
        raise SlideMakerError(f"invalid fit '{fit}' (must be one of {sorted(VALID_FITS)})", slide_index=idx)
    if "fit" in fm and layout != "image":
        msg = "fit is only used by layout 'image'"
        if strict:
            raise SlideMakerError(msg, slide_index=idx)
        warnings.append(msg)

    image_alt = fm.get("image_alt", "")
    if fm.get("image") and not image_alt:
        msg = "image set without image_alt"
        if strict:
            raise SlideMakerError(msg, slide_index=idx)
        warnings.append(msg)

    for i, item in enumerate(images):
        if not item.alt:
            msg = f"images[{i}] set without alt"
            if strict:
                raise SlideMakerError(msg, slide_index=idx)
            warnings.append(msg)

    slide = SlideConfig(
        index=idx,
        layout=layout,
        title=fm.get("title"),
        kicker=fm.get("kicker"),
        subtitle=fm.get("subtitle"),
        author=fm.get("author") or deck.default_author,
        date=fm.get("date"),
        image=fm.get("image"),
        image_alt=image_alt,
        image_label=fm.get("image_label"),
        images=images,
        video=fm.get("video"),
        panels=panels,
        background=fm.get("background"),
        background_opacity=opacity,
        fit=fit,
        formula=fm.get("formula"),
        formula_note=fm.get("formula_note"),
        notes=fm.get("notes"),
        id=fm.get("id") or f"slide-{idx + 1}",
        classes=fm.get("classes", ""),
        body=raw_slide.body,
        warnings=warnings,
    )

    if slide.date == "today":
        slide.date = date_cls.today().isoformat()

    if layout == "title":
        if not slide.title:
            raise SlideMakerError("layout 'title' requires a 'title' field", slide_index=idx)
    elif layout == "content":
        media_fields = [f for f in ("image", "panels", "video", "images") if fm.get(f)]
        if len(media_fields) > 1:
            raise SlideMakerError(
                "layout 'content' may only set one of image/panels/video/images, got: "
                + ", ".join(media_fields),
                slide_index=idx,
            )
        if slide.images and len(slide.images) != 2:
            raise SlideMakerError(
                f"'images' currently supports exactly 2 images (got {len(slide.images)})",
                slide_index=idx,
            )
    elif layout == "split":
        if not slide.panels:
            raise SlideMakerError("layout 'split' requires a non-empty 'panels' list", slide_index=idx)
    elif layout == "image":
        if not slide.image:
            raise SlideMakerError("layout 'image' requires an 'image' field", slide_index=idx)
        if slide.background:
            raise SlideMakerError(
                "layout 'image' fills the whole slide with 'image' — 'background' would be "
                "redundant, remove one",
                slide_index=idx,
            )

    return slide
