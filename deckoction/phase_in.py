"""Expand a `phase_in` slide into one physical slide per reveal step.

Per layout: `content`/`stacked` reveal the body's bullets (below); `split` reveals one
panel per step (earlier panels dimmed, later ones hidden but keeping their space),
plus a final "everything undimmed" step; `image` cycles its `phase_images` full-bleed,
one per step, with no extra final step.

`phase_level` (1-indexed: 1 = top-level bullets, 2 = first sub-level, ...) picks the
bullet-nesting depth that drives the reveal. A bullet at exactly that depth is always
its own reveal step ("target"); a bullet shallower than the target depth that has no
children reaching it (a ragged/shallower branch) falls back to being its own step too;
any other bullet shallower than the target depth is purely structural and is
"backfilled" to appear alongside its first-revealed child, at every step, forever —
so an ancestor and its first child are always in lock-step (same dim/current/pending
state). Bullets deeper than the target depth get no tag of their own: they're DOM
descendants of their tagged ancestor `<li>`, so CSS dims/hides them for free.

One extra step (index == target_count) follows the per-bullet reveals: everything
undimmed, matching a normal (non-phase-in) content slide. `phase_images` is indexed by
the same step number, clamped to the last entry once exhausted, so this final step
naturally keeps the frozen last image too.
"""

from __future__ import annotations

import re
from dataclasses import replace

from .parser import SlideMakerError
from .render import _MD
from .schema import SlideConfig

_PHASE_LI_RE = re.compile(r'<li data-phase="(\d+)"')


def _parse_bullet_tree(tokens: list) -> list[dict]:
    """Flatten the token stream's bullet-list nesting into a tree of list-item
    entries (pre-order), each linked to its immediate children."""
    items: list[dict] = []
    stack: list[dict] = []
    depth = 0
    for i, tok in enumerate(tokens):
        if tok.type == "bullet_list_open":
            depth += 1
        elif tok.type == "bullet_list_close":
            depth -= 1
        elif tok.type == "list_item_open":
            entry = {"token_idx": i, "depth": depth, "children": [], "step": None}
            if stack:
                stack[-1]["children"].append(entry)
            items.append(entry)
            stack.append(entry)
        elif tok.type == "list_item_close":
            stack.pop()
    return items


def _resolve_steps(items: list[dict], target_depth: int) -> int:
    """Assign a 0-indexed reveal step to every item at or above target_depth, in
    document order. Returns the total number of distinct targets."""
    counter = 0

    def resolve(entry: dict) -> int:
        nonlocal counter
        if entry["step"] is not None:
            return entry["step"]
        is_target = entry["depth"] == target_depth or (
            entry["depth"] < target_depth and not entry["children"]
        )
        if is_target:
            entry["step"] = counter
            counter += 1
        else:
            entry["step"] = resolve(entry["children"][0])
        return entry["step"]

    for entry in items:
        if entry["depth"] <= target_depth:
            resolve(entry)
    return counter


def render_with_phase_tags(body: str, phase_level: int) -> tuple[str, int]:
    """Render a phase-in slide body, tagging each reveal-unit (and its backfilled
    ancestors) with `data-phase="N"`. Returns (html, target_count)."""
    tokens = _MD.parse(body)
    items = _parse_bullet_tree(tokens)
    target_count = _resolve_steps(items, phase_level)
    for entry in items:
        if entry["step"] is not None:
            tokens[entry["token_idx"]].attrSet("data-phase", str(entry["step"]))
    html = _MD.renderer.render(tokens, _MD.options, {})
    return html, target_count


def line_step_ranges(body: str, phase_level: int) -> tuple[list[tuple[int, int, int]], int]:
    """For a phase_in body, the source line span of every reveal-unit (target or
    backfilled ancestor) and the step it resolves to — lets a caller correlate
    something at a given source line (e.g. a citation) to the step whose bullet it
    lives in. Ranges nest (an ancestor's span contains its children's); a line inside
    more than one range belongs to the *smallest* (most specific) one. Returns
    (ranges, target_count)."""
    tokens = _MD.parse(body)
    items = _parse_bullet_tree(tokens)
    target_count = _resolve_steps(items, phase_level)
    ranges = []
    for entry in items:
        if entry["step"] is not None:
            tok_map = tokens[entry["token_idx"]].map
            if tok_map:
                ranges.append((tok_map[0], tok_map[1], entry["step"]))
    return ranges, target_count


def step_for_line(ranges: list[tuple[int, int, int]], line: int) -> int | None:
    """The step of the smallest range in `ranges` (as returned by `line_step_ranges`)
    containing `line`, or None if no range covers it."""
    best_step = None
    best_span = None
    for start, end, step in ranges:
        if start <= line < end:
            span = end - start
            if best_span is None or span < best_span:
                best_step, best_span = step, span
    return best_step


BULLET_LAYOUTS = ("content", "stacked")


def step_layout(slide: SlideConfig) -> tuple[int, int]:
    """(step_count, final_step) for a phase_in slide, where `final_step` is the
    index of the "everything undimmed" step (== step_count for the image layout,
    which has none). Shared by `expand_slide` and citation processing so the two
    can't disagree on how many steps a slide has."""
    if slide.layout in BULLET_LAYOUTS:
        _, target_count = render_with_phase_tags(slide.body, slide.phase_level)
        if target_count == 0:
            raise SlideMakerError("phase_in requires at least one bullet point in the body", slide_index=slide.index)
        return target_count + 1, target_count
    if slide.layout == "split":
        return len(slide.panels) + 1, len(slide.panels)
    if slide.layout == "image":
        return len(slide.phase_images), len(slide.phase_images)
    raise SlideMakerError(f"phase_in is not supported on layout '{slide.layout}'", slide_index=slide.index)


def panel_phase_class(index: int, step: int, final_step: int) -> str:
    """CSS class for split-layout panel `index` at reveal step `step`."""
    if step >= final_step or index == step:
        return ""
    return "phase-dim" if index < step else "phase-pending"


def bullet_phase_classes(body_html: str, step: int, target_count: int) -> str:
    """Mark bullets `phase-dim`/`phase-pending` for reveal step `step` (0-indexed) of
    `target_count` targets. `step == target_count` is the final "everything
    undimmed" step, left untouched."""

    def repl(match: re.Match) -> str:
        if step >= target_count:
            return match.group(0)
        phase = int(match.group(1))
        if phase < step:
            return f'{match.group(0)} class="phase-dim"'
        if phase > step:
            return f'{match.group(0)} class="phase-pending"'
        return match.group(0)

    return _PHASE_LI_RE.sub(repl, body_html)


def expand_slide(slide: SlideConfig) -> list[SlideConfig]:
    """Expand one phase_in slide into one physical clone per reveal step (see
    `step_layout`). A non-phase-in slide passes through unchanged."""
    if not slide.phase_in:
        return [slide]

    step_count, _ = step_layout(slide)
    clones = []
    for step in range(step_count):
        changes = {}
        # Only content/image use phase_images (schema forbids them elsewhere, and
        # forbids `image` alongside them), so other clones keep their fields as-is.
        # Each step sets every media field, so an earlier step's equation/image
        # never leaks into a later one.
        if slide.phase_images:
            entry = slide.phase_images[min(step, len(slide.phase_images) - 1)]
            if len(entry) == 1 and entry[0].equation:
                changes = dict(
                    equation=entry[0].equation,
                    image=None,
                    image_alt="",
                    image_label=None,
                    image_reference="",
                    images=[],
                )
            elif len(entry) == 1:
                changes = dict(
                    equation=None,
                    image=entry[0].image,
                    image_alt=entry[0].alt,
                    image_label=entry[0].label,
                    image_reference=entry[0].reference,
                    images=[],
                )
            else:
                # An `images` group: rendered through the same path as the `images`
                # field (rows chosen by build.arrange_images).
                changes = dict(
                    equation=None, image=None, image_alt="", image_label=None, image_reference="", images=entry
                )
        clones.append(
            replace(
                slide,
                id=f"{slide.id}-{step + 1}",
                phase_step=step,
                phase_step_count=step_count,
                citation_numbers=slide.citation_numbers_by_step.get(step, []),
                **changes,
            )
        )
    return clones


def expand_all(slide_configs: list[SlideConfig]) -> list[SlideConfig]:
    """Flat-map `expand_slide` over the deck, then renumber `.index` sequentially
    over the resulting physical order. `.display_index` is left untouched, so every
    clone of one authored slide keeps sharing the same author-order number."""
    expanded = [clone for slide in slide_configs for clone in expand_slide(slide)]
    return [replace(slide, index=i) for i, slide in enumerate(expanded)]
