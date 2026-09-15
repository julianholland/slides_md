"""Expand a `phase_in` content slide into one physical slide per reveal step.

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
    """Expand one phase_in slide into `target_count + 1` physical clones. A
    non-phase-in slide passes through unchanged."""
    if not slide.phase_in:
        return [slide]

    _, target_count = render_with_phase_tags(slide.body, slide.phase_level)
    if target_count == 0:
        raise SlideMakerError("phase_in requires at least one bullet point in the body", slide_index=slide.index)

    step_count = target_count + 1
    clones = []
    for step in range(step_count):
        image_entry = slide.phase_images[min(step, len(slide.phase_images) - 1)] if slide.phase_images else None
        clones.append(
            replace(
                slide,
                id=f"{slide.id}-{step + 1}",
                phase_step=step,
                phase_step_count=step_count,
                image=image_entry.image if image_entry else None,
                image_alt=image_entry.alt if image_entry else "",
                image_label=image_entry.label if image_entry else None,
                image_reference=image_entry.reference if image_entry else "",
            )
        )
    return clones


def expand_all(slide_configs: list[SlideConfig]) -> list[SlideConfig]:
    """Flat-map `expand_slide` over the deck, then renumber `.index` sequentially
    over the resulting physical order. `.display_index` is left untouched, so every
    clone of one authored slide keeps sharing the same author-order number."""
    expanded = [clone for slide in slide_configs for clone in expand_slide(slide)]
    return [replace(slide, index=i) for i, slide in enumerate(expanded)]
