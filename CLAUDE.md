# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`slide_maker` turns a single Markdown file (slides separated by `+++`, each with YAML
frontmatter) into a static HTML slide deck. The output is plain HTML/CSS/vanilla JS —
no client-side framework — deliberately matching the hand-built reference deck at
`../sulfur_slides` (dark theme, click/keyboard nav, vendored KaTeX, no build step or CDN
dependency in the generated output).

## Commands

```bash
pip install -e ".[dev]"                                    # install + dev deps (pytest)
pytest                                                      # run all tests
pytest tests/test_build_end_to_end.py::test_build_demo_deck # run a single test
python -m slide_maker build examples/demo/slides.md -o build/demo --serve   # build + preview at :8000
```

No lint/format tooling is configured.

## Architecture

Pipeline (`slide_maker/build.py:build`): read `slides.md` (+ optional `deck.yaml`) →
split on `+++` (`parser.py`) → validate per-slide YAML frontmatter (`schema.py`) →
render Markdown body + LaTeX (`render.py`) → render each slide via its layout's Jinja
template (`layouts.py` maps layout name → template) → assemble `base.html.jinja` → write
`index.html`, copy `assets/` and `vendor/katex/` verbatim, copy only the
images actually referenced into `<output>/slide_images/`.

**Five layouts**, each with its own template in `slide_maker/templates/`:
`title` (centered, translucent panel, background, author/date), `content` (bullets +
boxed image/video/panels, default), `stacked` (full-width bullets + optional KaTeX
`formula` block), `split` (2-3 comparison panels, no bullets), `image` (single image
fills the whole slide edge-to-edge, sized by `fit`: `contain` default or `cover`;
optional `title`/`kicker` overlay caption).

**Background-image-with-alpha** (`background` + `background_opacity`, any layout) and
the `image` layout's full-bleed image are the *same* mechanism: a `.bg-layer` div
rendered in `base.html.jinja`, sibling to `.slide-content`. For the `image` layout,
`build.py:_slide_context` routes `slide.image` through this same background path rather
than the boxed `.media-col` image — schema validation (`schema.py`) forbids setting both
`image` and `background` on that layout since they'd be redundant.

**Known CSS trap — do not "fix" this back**: `.bg-layer`'s `background-image` and
`opacity` are set via inline `style="..."` on the div in `base.html.jinja`, NOT via CSS
custom properties consumed in `assets/style.css`. A `url()` value inside a custom
property resolves relative to the *stylesheet* that consumes it via `var()`
(`assets/style.css`, under `assets/`), not the HTML page — so it would 404 against
`slide_images/` at the output root. This was a real, non-obvious bug found via headless-
Chromium screenshot verification; `tests/test_build_end_to_end.py::test_background_image_uses_inline_style_not_css_custom_property`
guards against reintroducing it.

**Markdown body rendering** (`render.py`): `markdown-it-py` with a `bullet_list_open`
render-rule override that adds `class="bullets"` only when `token.level == 0`, so nested
`<ul>`s stay bare and pick up the reference CSS's descendant-selector styling. Block
math uses a separate `formula` YAML field (raw LaTeX, no `$$`) rather than `$$...$$` in
the body, because CommonMark's underscore-emphasis parsing mangles LaTeX subscripts like
`q_{min}`; inline `$...$` in the body is left untouched and rendered client-side by
KaTeX's `auto-render` in `assets/script.js`.

**Image handling** (`build.py:ImageResolver`): only images actually referenced by a
slide get resolved (relative to `--images-dir`, default the input file's directory) and
copied into `<output>/slide_images/`, deduplicated by source path; a missing referenced
image is always a fatal build error, `--strict` or not; a basename collision between two
different source files is also fatal.

**Two-image `images` pair** (`content` layout only, exactly 2 entries): `ImageResolver.resolve_with_size`
reads each image's real pixel dimensions via `slide_maker/imagesize.py` — a small
dependency-free PNG/JPEG/GIF header parser (deliberately not Pillow, to keep the project
at 3 runtime deps). `build.py:choose_image_pair_arrangement` picks `stack` (vertical) vs
`side` (horizontal) by comparing the combined side-by-side aspect ratio to 1 — this is a
pure function, unit-tested directly. Each `images[]` entry reuses the same `Panel`
dataclass as `split`'s `panels` (`image`/`label`/`alt`) rather than a separate type,
since the shape is identical; the single boxed `image` field has its own parallel
`image_label` for a caption. Both render via a shared `.panel-label` CSS class.

**Click-to-zoom lightbox**: a single `#lightbox` element in `base.html.jinja` (once per
page, not per slide); `assets/script.js` attaches a click handler to every
`.slide-content img` that opens it fit-to-screen, and guards the existing arrow-key slide
navigation so it's suppressed while the lightbox is open (`Escape` or a backdrop click
closes it instead). Inside the lightbox, clicking the image or scrolling over it further
zooms via CSS `transform: scale()` with `transform-origin` tracked to the cursor/click
position (`setZoom`/`originFromEvent` in `script.js`) — a click on the already-zoomed
image resets to fit. This is a click/wheel affordance only, not drag-to-pan: zoomed
content that extends past the viewport is simply clipped (`html, body` has
`overflow: hidden`), so keep `MAX_ZOOM` modest if touching this.

**`fit` on the `image` layout**: controls `background-size` on that layout's `.bg-layer`
(`contain` = "fit to screen", the default, vs `cover` = "fill the screen", cropping) —
applied as an inline style override in `base.html.jinja` only when `slide.layout ==
'image'`, so other layouts' backgrounds keep the CSS default (`cover`, unchanged from
before this field existed). Schema validation warns (errors under `--strict`) if `fit` is
set on any other layout, since it's a no-op there.

**Validation** (`schema.py`): most bad frontmatter is fatal immediately (wrong
layout-specific field combos, out-of-range `background_opacity`, missing required
fields); soft issues (missing `image_alt`/`images[].alt`, unknown frontmatter keys) are
warnings unless `--strict` is passed, in which case they become errors too.

`examples/demo/slides.md` exercises all five layouts + background alpha + image pairs +
blockquotes + KaTeX, and doubles as the primary integration-test fixture
(`tests/test_build_end_to_end.py`) — keep it in sync when adding fields/layouts. See
`README.md` for the full per-slide field reference and CLI flags.
