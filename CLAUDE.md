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
pip install -e ".[dev]"                                    # install + dev deps (pytest, ruff)
pytest                                                      # run all tests
pytest tests/test_build_end_to_end.py::test_build_demo_deck # run a single test
ruff check .                                                # lint
python -m slide_maker build examples/demo/slides.md -o build/demo --serve   # build + preview at :8000

pip install -e ".[pdf]" && playwright install chromium      # needed for --pdf / --thumbnail
python -m slide_maker build examples/demo/slides.md -o build/demo --pdf demo.pdf --thumbnail demo.png
```

Ruff is configured in `pyproject.toml`'s `[tool.ruff]` — a deliberately modest baseline
(pyflakes `F` + import ordering `I` + a few pycodestyle error groups, not style/annotation
opinions) since the project had no prior lint history. No formatter is configured.
`.github/workflows/ci.yml` runs `pytest` (matrixed across Python 3.10-3.12), `ruff check`,
and a docs build (`sphinx-build -W`, warnings promoted to errors) on every push/PR.

## Architecture

Pipeline (`slide_maker/build.py:build`): read `slides.md` (+ optional `deck.yaml`) →
strip `<!-- ... -->` comments (`parser.py:strip_comments`, on the raw file text, before
anything else) → split on `+++` (`parser.py`) → validate per-slide YAML frontmatter
(`schema.py`) → render Markdown body + LaTeX (`render.py`) → render each slide via its
layout's Jinja template (`layouts.py` maps layout name → template) → assemble
`base.html.jinja` → write `index.html`, copy `assets/` and `vendor/katex/` verbatim, copy
only the images actually referenced into `<output>/slide_images/`.

**Comment stripping runs before the `+++` split**, deliberately: `COMMENT_RE = <!-{2,}.*?-{2,}>`
(DOTALL, so it spans lines) matches both `<!-- -->` and the `<!--- --->` variant. Because
it runs first, a comment can wrap a whole slide — its own `---`/`+++` fences included —
and that slide is simply never parsed; the two adjacent `+++` markers left behind collapse
into an empty chunk, already discarded by the existing "drop whitespace-only chunks"
filter. Known limitation, accepted rather than solved: this is a raw-text regex, not
Markdown-aware, so `<!-- -->` written inside inline code/fenced code in a slide body
would also get stripped (no test/code path special-cases that).

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

**PDFs as images** (`slide_maker/pdf_images.py`, `ImageResolver.resolve`): any
image-path field accepts a `.pdf` too — auto-detected by extension, no new YAML field,
since the goal is "reference a PDF exactly like you'd reference a PNG." Detection sits
*inside* `resolve()`, right after the existing real-file check and *before* the
basename-collision logic, so a rasterized `figure.pdf` → `figure.png` still correctly
collides with an unrelated real `figure.png` referenced elsewhere (their resolved
source paths differ) — every downstream step (`imagesize.get_size()` for the two-image
pair arrangement, `copy_into()`'s final copy) then operates on the rasterized PNG with
zero further changes, exactly as it would for a real PNG. Rasterization
(`pdf_images.rasterize_pdf`, PyMuPDF — `import pymupdf`, not the library's older
deprecated `fitz` alias) is first-page-only, fixed at 200 DPI, no per-image
configuration; `ImageResolver` caches by source PDF path (a PDF referenced on several
slides is rasterized once) into a lazily-created `tempfile.TemporaryDirectory` (never
allocated for a deck with no PDF images), cleaned up via `ImageResolver.close()` in a
`finally` in `build()`. PyMuPDF is a separate optional extra (`pip install -e
".[pdf-images]"`) from the `pdf` extra's Playwright — deliberately not reusing
Playwright/Chromium (screenshotting its built-in PDF viewer) to avoid tying a simple
raster conversion to a ~300MB browser download for a single-page-image use case.

**Placeholder images** (`slide_maker/placeholders.py`): any image-path field (`image`,
`background`, `images[].image`, `panels[].image`) accepts a LaTeX-`mwe`-style name —
`example-image` or `example-image-a`..`-z` — in place of a real path.
`ImageResolver.resolve` checks `placeholders.resolve_placeholder()` *before* touching the
filesystem, so these never need a file in `--images-dir`; the matched PNG comes from
`slide_maker/placeholder_images/` (27 files, pre-generated by
`scripts/generate_placeholders.py` — a dev-only script needing Pillow, which is deliberately
*not* a runtime dependency of the package). That directory is intentionally not under
`assets/` or `vendor/`, which `build.py` copies wholesale into every output — placeholders
are only copied when actually referenced, same as any other image, via the normal
resolver → `slide_images/` path. `build.py:_alt_text` auto-fills `alt` (e.g. "Placeholder
image C") from `placeholders.placeholder_alt()` whenever a placeholder is used without one,
and `schema.py`'s missing-alt warnings likewise skip placeholders — so dropping one in
while drafting never produces warnings to clean up later.

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

**Themes** (`slide_maker/themes.py`): a small registry (`THEME_PRESETS`, plain dict, same
idiom as `layouts.py`'s `TEMPLATE_BY_LAYOUT`) of named `ThemeDefinition`s (colors, a body
font, an optional watermark image). `schema.build_deck_config` resolves `deck.yaml`'s
`theme:` field: a string names a preset (`theme: alomancy`); a dict is the original
free-form CSS-override form, unrelated to any preset (kept byte-for-byte backward
compatible — only the keys given are emitted, nothing merged from a preset); omitting
`theme:` entirely emits no `<style>` override block and no watermark at all, identical to
output from before theming existed. The watermark image is subject to the same CSS trap
as `background` (above) — its `src` is a literal inline `<img>` in `base.html.jinja`, not
routed through `var()` in `style.css`. `deck.theme_font_body` is rendered with Jinja's
`| safe` filter (it only ever comes from a code-defined `ThemeDefinition`, never user
YAML) since Jinja's HTML-autoescaping would otherwise turn the font stack's `"`
characters into `&#34;` entities that a `<style>` block (a "raw text" element) never
decodes back; raw dict override *values*, which do come from user YAML, are validated
instead (rejecting `<`, `>`, `{`, `}`, `;`, newlines) rather than marked safe, since they
could otherwise break out of the `:root { ... }` rule.

**Phase-in reveal** (`phase_in: true`, `content` layout only, `slide_maker/phase_in.py`):
one authored slide expands into several *physical* `<section class="slide">`s — one per
bullet-reveal step, plus a final "everything undimmed" step — so keyboard/click nav and
`--pdf` see them as ordinary separate slides, while `data-display-index` (set on every
`<section>`, `= idx + 1` in author order, identical across one slide's expansion clones)
keeps the `current / total` counter UI on a single shared number; `assets/script.js`
derives `current`/`total` from that attribute (count of *distinct* values) instead of
raw DOM position, which is a strict superset of the old `slides.length`/`i+1` logic —
for a deck with no phase-in slides, `data-display-index` is just `i+1` for every slide,
byte-for-byte the same counter behavior as before this feature existed.
`phase_level` (1-indexed: `1` = top-level bullets, `2` = first sub-level, ...) picks the
bullet-nesting depth that drives the reveal: `phase_in.py` walks the parsed
markdown-it-py token stream (not the rendered HTML) into a tree keyed by real indent
depth (its own counter, not markdown-it's internal `token.level`, which jumps by 2 per
nesting — see the code comment), then assigns each bullet a `data-phase="N"` reveal-step
number in document order — a bullet at exactly the target depth is always its own step;
a shallower bullet with no children reaching that depth falls back to being its own step
too (a ragged tree just works); any other shallower bullet is purely structural and gets
*backfilled* to its first child's step, so an ancestor and its first-revealed descendant
are permanently in lock-step (same dim/current/pending state, forever — this is what
makes "the ancestor appears together with its first child" and "ancestors dim like
everything else" both fall out of one rule, no special-casing). Bullets deeper than the
target depth get no tag at all — CSS `.phase-dim`/`.phase-pending` on a tagged `<li>`
cascades to its untagged descendants for free. `build.py:_slide_context` diverts to
`phase_in.render_with_phase_tags`/`bullet_phase_classes` instead of the plain
`render.render_body` only when `slide.phase_step is not None`; ordinary slides are
untouched, and `render.py` itself needed no changes at all. `phase_images` (optional,
reuses the `Panel` dataclass like `images`/`panels`) is indexed by the same step number,
clamped to its last entry once exhausted — a 1-entry list is a valid way to keep one
static image on screen through the whole reveal. Warnings/body-syntax-checks in
`_slide_context` are only surfaced on a phase-in slide's first expansion clone (`step ==
0`), not once per physical clone — `dataclasses.replace()` gives every clone the same
`warnings` list object, so without this guard the same message would repeat once per
reveal step.

**Citations** (`bibliography:` in `deck.yaml`, `slide_maker/references.py`): a
`bibliography:` file (`.bib` → hand-rolled BibTeX parser formatted per ACS style,
anything else → a plain `"key": "citation"[: "doi"]` line format) supplies numbered
references, cited from a slide body via `[@key]`/`[@key1; @key2]` or from an image via
its `reference`/`image_reference` field (the latter reuses the same `.image`/`.image_alt`
sharing trick the `image` layout already uses — see "Background-image-with-alpha" above
— so one field covers both the boxed single image and the full-bleed `image`-layout
image). Numbering + in-body substitution is its own pipeline pass
(`references.process_citations`), run in `build.py` right after `validate_slide` and
*before* `phase_in.expand_all` — deliberately: phase-in's clones share one `.body` string
via `dataclasses.replace`, so substituting `[@key]` once, pre-expansion, means every
physical step of a phase-in slide gets the identical already-numbered markup and the
identical footnote set for free (a deliberate simplification — footnotes don't try to
track which bullets have actually revealed yet on a given step). Numbers are assigned
lazily, first-seen order, scanning each slide's body text first, then its image-bearing
fields in field order (`image_reference`, then `images[]`/`panels[]`/`phase_images[]`
entries) — citing an unknown key, or citing anything at all with no `bibliography:`
configured, is a fatal `SlideMakerError`, not a warning. The `[@key]` substitution
writes the *final* `<sup class="citation">[...]</sup>` markup (numbers already resolved)
directly into the raw body text before `render_body()` ever runs, relying on
markdown-it-py's `commonmark` preset passing raw HTML through untouched by default (the
same mechanism the `examples/cheatsheet/slides.md` `<code>&lt;!--...--&gt;</code>` trick
uses) — this needs no placeholder-then-patch two-pass approach, since numbering is fully
known upfront. A new `layout: references` slide (`slide_references.html.jinja`) renders
the full deck-ordered bibliography from a `references=` value passed into
`template.render()` directly (not nested under `deck`, since it's build-computed state,
not a `deck.yaml` setting) — nothing is auto-injected; the author places this slide
wherever they want (typically last), matching every other feature here being opt-in and
visible in the authored files. Per-slide footnotes (`.citation-footnotes`, bottom-left,
mirroring `.slide-counter`'s bottom-right) and per-image number badges
(`.citation-badge`, top-right, needing `position: relative` added to the three image
wrapper divs that didn't have it) are ordinary DOM content, so `--pdf`/`--thumbnail`
need no changes — but they *do* sit outside `.slide-content`, so `pdf.py`'s `_FIT_JS`
auto-shrink pass (scoped to `.slide-content`) doesn't reach them, same as
`.slide-counter` is already exempt today for the same structural reason. Known,
undocumented-further limitation: no `@string` macro expansion, no BibTeX
cross-references, no LaTeX accent unescaping, and journal names are used exactly as
given (no CASSI abbreviation lookup) — a deliberately partial BibTeX parser, not the
full spec.

**Validation** (`schema.py`): most bad frontmatter is fatal immediately (wrong
layout-specific field combos, out-of-range `background_opacity`, missing required
fields); soft issues (missing `image_alt`/`images[].alt`, unknown frontmatter keys) are
warnings unless `--strict` is passed, in which case they become errors too.

**PDF export** (`--pdf PATH`, `slide_maker/pdf.py:export_pdf`) and **thumbnail export**
(`--thumbnail PATH`, `slide_maker/thumbnail.py:export_thumbnail`) share one pattern: spin
up a throwaway `ThreadingHTTPServer` on `output_dir` (a built deck can't be screenshotted
via `file://` because `assets/script.js`/KaTeX fetches are same-origin-relative), drive
headless Chromium through Playwright (`sync_playwright`) to load `index.html`, then tear
the server down in a `finally`. Both are optional CLI flags on `build`, run in that
order — `--pdf` then `--thumbnail` — after the build and before `--serve`
(`slide_maker/cli.py`); both raise `SlideMakerError` with an install hint
(`pip install -e ".[pdf]"` + `playwright install chromium`) if Playwright isn't
installed, since the `pdf` extra is optional and not a runtime dependency.
`export_pdf` additionally emulates print media and injects `_FIT_JS`, which shrinks the
rem-based font sizes of a fixed selector list of elements (not CSS `transform: scale()`)
on any slide whose content overflows its `.slide-content` box — see the in-code comment
on `_TEXT_SELECTOR`/`_FIT_JS` for why `transform` and a minimum-scale floor were both
tried and rejected (Chromium's print paginator fragments based on unscaled layout height,
duplicating/overlapping content across a forced page break). `export_thumbnail` is
simpler — no print emulation or fit logic — since it only screenshots slide 1 at a fixed
`viewport` (default 1600x900) and the deck always opens there; both are exercised by
`tests/test_pdf_export.py` / `tests/test_thumbnail_export.py`, which `pytest.importorskip`
Playwright and skip outright if Chromium isn't installed locally.

`examples/demo/slides.md` exercises all six layouts + background alpha + image pairs +
placeholder images + phase-in reveal + citations/references + `<!-- -->` comments
(inline and a whole commented-out slide) + blockquotes + KaTeX, and doubles as the
primary integration-test fixture
(`tests/test_build_end_to_end.py`) — keep it in sync when adding fields/layouts. See
`README.md` for the full per-slide field reference and CLI flags.
