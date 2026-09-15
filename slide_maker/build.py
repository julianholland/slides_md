"""Orchestrates: parse -> validate -> render -> copy assets/images -> write output."""

from __future__ import annotations

import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

from . import imagesize, pdf_images, phase_in, placeholders
from . import references as references_mod
from . import render as render_mod
from .layouts import TEMPLATE_BY_LAYOUT
from .parser import SlideMakerError, load_deck_config, parse_slides_file
from .references import CitationContext
from .schema import DeckConfig, SlideConfig, build_deck_config, validate_slide

PACKAGE_DIR = Path(__file__).resolve().parent


@dataclass
class BuildResult:
    output_dir: Path
    slide_count: int
    warnings: list[str] = field(default_factory=list)


class ImageResolver:
    """Resolves slide-referenced image paths against images_dir and stages copies
    into output_dir/slide_images, deduplicating by source path and rejecting
    basename collisions between distinct source files.
    """

    def __init__(self, images_dir: Path):
        self.images_dir = images_dir
        self._by_basename: dict[str, Path] = {}
        self._pdf_cache: dict[Path, Path] = {}
        self._pdf_scratch_dir: tempfile.TemporaryDirectory | None = None

    def _rasterize_pdf(self, pdf_path: Path, slide_index: int) -> Path:
        cached = self._pdf_cache.get(pdf_path)
        if cached is not None:
            return cached
        if self._pdf_scratch_dir is None:
            self._pdf_scratch_dir = tempfile.TemporaryDirectory(prefix="slide_maker_pdf_")
        png_path = pdf_images.rasterize_pdf(pdf_path, Path(self._pdf_scratch_dir.name), slide_index=slide_index)
        self._pdf_cache[pdf_path] = png_path
        return png_path

    def close(self) -> None:
        if self._pdf_scratch_dir is not None:
            self._pdf_scratch_dir.cleanup()

    def resolve(self, rel_path: str, slide_index: int) -> str:
        placeholder = placeholders.resolve_placeholder(rel_path)
        if placeholder is not None:
            src = placeholder
        else:
            src = (self.images_dir / rel_path).resolve()
            if not src.is_file():
                raise SlideMakerError(f"referenced image not found: {rel_path}", slide_index=slide_index)
            if src.suffix.lower() == ".pdf":
                src = self._rasterize_pdf(src, slide_index)
        basename = src.name
        existing = self._by_basename.get(basename)
        if existing is not None and existing != src:
            raise SlideMakerError(
                f"image basename collision: '{basename}' refers to two different "
                f"source files ({existing} and {src})",
                slide_index=slide_index,
            )
        self._by_basename[basename] = src
        return f"slide_images/{basename}"

    def resolve_with_size(self, rel_path: str, slide_index: int) -> tuple[str, tuple[int, int]]:
        dest = self.resolve(rel_path, slide_index)
        src = self._by_basename[Path(dest).name]
        try:
            size = imagesize.get_size(src)
        except imagesize.ImageSizeError as exc:
            raise SlideMakerError(str(exc), slide_index=slide_index) from exc
        return dest, size

    def copy_into(self, output_dir: Path) -> None:
        dest_dir = output_dir / "slide_images"
        dest_dir.mkdir(parents=True, exist_ok=True)
        for basename, src in self._by_basename.items():
            shutil.copy2(src, dest_dir / basename)


def _alt_text(explicit: str, source: str, fallback: str = "") -> str:
    """Explicit alt text wins; a placeholder source (e.g. 'example-image-a') gets a
    sensible auto-generated alt when none was given; otherwise fall back."""
    return explicit or placeholders.placeholder_alt(source) or fallback


def choose_image_pair_arrangement(ratio_a: float, ratio_b: float) -> str:
    """Pick 'stack' (vertical) or 'side' (horizontal) for a 2-image pair.

    Scaled to a common height of 1, laying the images side by side gives a
    combined width of ratio_a + ratio_b. If that combination would be wider
    than it is tall, each image would get squeezed thin in the media column,
    so stack them vertically instead; otherwise side by side already fits.
    """
    return "stack" if (ratio_a + ratio_b) > 1.0 else "side"


def _citation_badge(key: str, citations: CitationContext) -> SimpleNamespace | None:
    if not key:
        return None
    number = citations.key_to_number.get(key)
    if number is None:
        return None
    return SimpleNamespace(number=number, doi_url=citations.by_number[number].doi_url)


def _slide_context(
    slide: SlideConfig, resolver: ImageResolver, strict: bool, warnings: list[str], citations: CitationContext
) -> SimpleNamespace:
    # A phase-in slide expands into several physical clones sharing one body/warnings
    # list — only surface these once (on the first step), not once per physical clone.
    report_warnings = slide.phase_step is None or slide.phase_step == 0

    if report_warnings:
        for w in slide.warnings:
            warnings.append(f"slide {slide.display_index}: {w}")

    body_warnings = render_mod.check_unsupported_body_syntax(slide.body)
    for w in body_warnings:
        if strict:
            raise SlideMakerError(w, slide_index=slide.index)
        if report_warnings:
            warnings.append(f"slide {slide.display_index}: {w}")

    # The 'image' layout fills the whole slide with `image` via the same full-bleed
    # mechanism as `background` (schema validation guarantees only one is set).
    background = None
    if slide.layout == "image":
        background = resolver.resolve(slide.image, slide.index)
    elif slide.background:
        background = resolver.resolve(slide.background, slide.index)

    image = None
    if slide.layout != "image" and slide.image:
        image = resolver.resolve(slide.image, slide.index)

    images = []
    image_pair_arrangement = None
    if slide.images:
        dest_a, (wa, ha) = resolver.resolve_with_size(slide.images[0].image, slide.index)
        dest_b, (wb, hb) = resolver.resolve_with_size(slide.images[1].image, slide.index)
        image_pair_arrangement = choose_image_pair_arrangement(wa / ha, wb / hb)
        images = [
            SimpleNamespace(
                src=dest_a,
                alt=_alt_text(slide.images[0].alt, slide.images[0].image),
                label=slide.images[0].label,
                reference=_citation_badge(slide.images[0].reference, citations),
            ),
            SimpleNamespace(
                src=dest_b,
                alt=_alt_text(slide.images[1].alt, slide.images[1].image),
                label=slide.images[1].label,
                reference=_citation_badge(slide.images[1].reference, citations),
            ),
        ]

    panels = [
        SimpleNamespace(
            image=resolver.resolve(p.image, slide.index),
            label=p.label,
            alt=_alt_text(p.alt, p.image, fallback=p.label),
            reference=_citation_badge(p.reference, citations),
        )
        for p in slide.panels
    ]

    formula_html = render_mod.render_formula(slide.formula) if slide.formula else None

    if slide.phase_step is not None:
        raw_html, _ = phase_in.render_with_phase_tags(slide.body, slide.phase_level)
        body_html = phase_in.bullet_phase_classes(raw_html, slide.phase_step, slide.phase_step_count - 1)
    else:
        body_html = render_mod.render_body(slide.body)

    citation_footnotes = [
        SimpleNamespace(number=n, entry=citations.by_number[n]) for n in slide.citation_numbers
    ]

    return SimpleNamespace(
        index=slide.index,
        display_index=slide.display_index,
        id=slide.id,
        layout=slide.layout,
        classes=slide.classes,
        title=slide.title,
        kicker=slide.kicker,
        subtitle=slide.subtitle,
        author=slide.author,
        date=slide.date,
        image=image,
        image_alt=_alt_text(slide.image_alt, slide.image or ""),
        image_label=slide.image_label,
        image_reference=_citation_badge(slide.image_reference, citations),
        images=images,
        image_pair_arrangement=image_pair_arrangement,
        video=slide.video,
        panels=panels,
        background=background,
        background_opacity=slide.background_opacity,
        fit=slide.fit,
        body_html=body_html,
        formula_html=formula_html,
        formula_note=slide.formula_note,
        notes=slide.notes,
        phase_step=slide.phase_step,
        phase_step_count=slide.phase_step_count,
        citation_footnotes=citation_footnotes,
    )


def build(
    input_path: Path,
    output_dir: Path,
    config_path: Path | None = None,
    images_dir: Path | None = None,
    strict: bool = False,
    force: bool = False,
) -> BuildResult:
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if config_path is None:
        default_config = input_path.with_name("deck.yaml")
        config_path = default_config if default_config.exists() else None

    if images_dir is None:
        images_dir = input_path.parent

    if output_dir.exists():
        if any(output_dir.iterdir()) and not force:
            raise SlideMakerError(
                f"output directory '{output_dir}' already exists and is not empty "
                "(pass --force to overwrite)"
            )
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_slides = parse_slides_file(input_path)
    deck_raw = load_deck_config(config_path)
    deck: DeckConfig = build_deck_config(deck_raw, config_dir=config_path.parent if config_path else None)

    bibliography = references_mod.load_bibliography(deck.bibliography_path) if deck.bibliography_path else None

    warnings: list[str] = []
    resolver = ImageResolver(images_dir)
    try:
        slide_configs = [validate_slide(rs, deck, strict) for rs in raw_slides]
        slide_configs, citations = references_mod.process_citations(slide_configs, bibliography, strict)
        slide_configs = phase_in.expand_all(slide_configs)
        slide_contexts = [_slide_context(s, resolver, strict, warnings, citations) for s in slide_configs]

        env = Environment(
            loader=FileSystemLoader(PACKAGE_DIR / "templates"),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = env.get_template("base.html.jinja")
        html = template.render(
            deck=deck, slides=slide_contexts, layout_templates=TEMPLATE_BY_LAYOUT, references=citations.ordered
        )

        (output_dir / "index.html").write_text(html, encoding="utf-8")

        assets_dest = output_dir / "assets"
        if assets_dest.exists():
            shutil.rmtree(assets_dest)
        shutil.copytree(PACKAGE_DIR / "assets", assets_dest)

        vendor_dest = output_dir / "vendor"
        if vendor_dest.exists():
            shutil.rmtree(vendor_dest)
        shutil.copytree(PACKAGE_DIR / "vendor", vendor_dest)

        resolver.copy_into(output_dir)
    finally:
        resolver.close()

    return BuildResult(output_dir=output_dir, slide_count=len(slide_configs), warnings=warnings)


def print_warnings(warnings: list[str]) -> None:
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
