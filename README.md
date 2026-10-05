# slide_maker

[![CI](https://github.com/julianholland/slides_md/actions/workflows/ci.yml/badge.svg)](https://github.com/julianholland/slides_md/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/slides-md/badge/?version=latest)](https://slides-md.readthedocs.io/en/latest/?badge=latest)

**Full documentation: [slides-md.readthedocs.io](https://slides-md.readthedocs.io/)**

Turn a single Markdown file into a static HTML slide deck. No client-side framework —
just the same vanilla HTML/CSS/JS approach as the hand-built [`sulfur_slides`](../sulfur_slides)
deck it's based on: a dark theme, keyboard/click navigation, click-to-zoom images, and
vendored KaTeX for math, with no build step or CDN dependency in the output.

## Quickstart

```bash
uv sync
uv run slides_md examples/demo/slides.md            # add --force to rebuild over a previous build
```

This builds `examples/demo/build/index.html` (plus `assets/`, `vendor/katex/`, and
`slide_images/`) and serves it at `http://localhost:8000`. `examples/demo/slides.md`
exercises every layout and feature in one deck — a good starting point to copy from.

## Authoring format

Write one Markdown file (e.g. `slides.md`). Slides are separated by a line containing
exactly `+++`. Each slide has YAML frontmatter (fenced by `---`/`---`) followed by a
Markdown body:

```markdown
---
layout: content
kicker: Overview
title: Why a Markdown Slide Tool
image: images/diagram.png
image_alt: Diagram of the pipeline
---

- Author once in a single Markdown file
  - YAML frontmatter per slide controls layout and media
- Generator assembles static HTML/CSS/JS

+++

---
layout: title
title: My Presentation
subtitle: A subtitle
author: Jane Doe
date: today
background: images/hero.jpg
---
```

The body supports paragraphs, up to two levels of bullet lists, inline `**bold**` /
`*em*` / inline code, inline KaTeX `$...$` (rendered client-side, so any valid LaTeX
passes through untouched), and `> ` blockquotes (rendered as an italic grey callout box,
matching the KaTeX formula box style), and GFM pipe tables (`| a | b |` rows with a
`|---|:-:|` separator line; column alignment and inline math in cells both work). Don't use Markdown headings or `![]()` images in
the body — use the `title`/`kicker`/`image` fields instead (the generator warns if it
sees either).

Anything wrapped in `<!-- ... -->` (or `<!--- ... --->`) is stripped before the file is
even split into slides, so it's never parsed or rendered — comment out a note-to-self
inside a slide's body, a YAML field, or a whole slide (fences included) and it's simply
gone from the build.

### Layouts

| `layout`  | What it renders |
|---|---|
| `title`   | Centered title over a full-bleed background, in a translucent panel, with optional `subtitle`, `author`, `date` |
| `content` | `title`/`kicker` + bullets on the left, a single `image`, two `images`, `video`, or `panels` comparison on the right (default layout) |
| `stacked` | `title`/`kicker` + full-width bullets, no media column — also where block math (`formula`) usually goes |
| `split`   | `title`/`kicker` + a full-width row of 2-3 `panels` (image + caption), no bullets |
| `image`   | A single `image` fills the entire slide edge-to-edge, sized via `fit` (`contain`, default — fit to screen, no cropping; or `cover` — fill the screen, cropping if needed); `title`/`kicker` are optional, shown as a small overlay panel — omit both for a bare full-slide image |
| `references` | Renders the full numbered bibliography (see [Citations & references](#citations--references)) — no fields of its own to set |

### Per-slide fields

| field | applies to | notes |
|---|---|---|
| `layout` | all | `title` / `content` / `stacked` / `split` / `image` / `references`; default `content` |
| `title` | all | required for `title` layout; optional caption for `image` |
| `kicker` | content/stacked/split/image | small uppercase label above the title |
| `subtitle` | title | |
| `author` | title | falls back to `deck.yaml`'s `default_author` |
| `date` | title | literal string, or `today` to fill in the build date |
| `image` / `image_alt` / `image_label` / `image_reference` | content, image | on `content`, a boxed image with an optional caption `image_label` (mutually exclusive with `video`/`panels`/`images`/`phase_in`); on `image`, the full-bleed slide image (required unless `phase_in` is set, mutually exclusive with `background`/`phase_images`). Accepts a placeholder name or a `.pdf` file in place of a real image path. `image_reference` cites a bibliography key, numbering it in the image's top-right corner |
| `images` | content | exactly 2 `{image, label?, alt?, reference?}`; auto-arranged stacked or side-by-side from aspect ratio (mutually exclusive with `image`/`video`/`panels`/`phase_in`) |
| `video` | content | mutually exclusive with `image`/`panels`/`images`/`phase_in` |
| `panels` | content, split | list of `{image, label, alt?, reference?}`; required for `split` |
| `background` | all except `image` | image path (or `.pdf`); layers behind the slide content |
| `background_opacity` | all | `0.0`-`1.0`, default `1.0` |
| `fit` | image | `contain` (default, fit to screen) or `cover` (fill the screen) |
| `formula` | content/stacked | raw LaTeX (no `$$`), rendered in a `.formula-box` |
| `formula_note` | content/stacked | small caption under the formula |
| `notes` | all | speaker notes, emitted as an HTML comment (not visible) |
| `id` / `classes` | all | override the slide's `id`, or add extra CSS classes |
| `phase_in` | content, stacked, split, image | `true` to reveal the slide step by step — bullets on `content`/`stacked`, panels on `split`, `phase_images` on `image`; see [Phase-in reveal](#phase-in-reveal). On `content`, mutually exclusive with `image`/`video`/`images`/`panels` |
| `phase_level` | content, stacked | with `phase_in: true`: which bullet-indent level drives the reveal (`1` = top-level, default; `2` = first sub-level; ...) |
| `phase_images` | content, image | with `phase_in: true`: list of `{image, alt?, reference?}` shown one per reveal step. On `content`, it stays on the last image once the list runs out; on `image`, it's required and each entry is one full-bleed step |

Any slide can carry a `background` + `background_opacity` — this is independent of the
title slide's translucent panel, so a dimmed background works on content slides too.

A `content` slide's `images` pair is auto-arranged from each image's actual pixel
dimensions (read at build time, no dependency needed): if the two images placed side by
side would come out wider than tall, they're stacked vertically instead so neither gets
squeezed thin in the media column; otherwise they sit side by side.

Every rendered `<img>` is click-to-zoom — clicking it opens a full-screen lightbox fit to
the screen. Inside the lightbox, click the image (or scroll the mouse wheel over it) to
zoom in further, centered on the cursor; click again to zoom back out. Click the dark
backdrop or press `Escape` to close.

### Phase-in reveal

Setting `phase_in: true` on a `content` slide turns its body bullets into a build/reveal
sequence: the deck steps through them one at a time (each step is its own slide for
navigation and `--pdf` purposes, but they all share one number in the `current / total`
counter). Write the bullets exactly as usual — no special syntax:

```markdown
---
layout: content
title: Rollout Plan
phase_in: true
phase_images:
  - image: images/step1.png
  - image: images/step2.png
---

- First we do X
  - a supporting detail
- Then Y
- Finally Z
```

This produces 4 physical steps: bullet 1 revealed → bullet 2 revealed (bullet 1 dims) →
bullet 3 revealed (bullets 1-2 dim) → everything undimmed (the settled final view).
`phase_images` is optional and cycles one image per step, freezing on the last entry
once the list runs out — a single-entry list just keeps one static image on screen
throughout. Sub-bullets always reveal together with their parent bullet.

`phase_level` changes which indent level drives the reveal (default `1`, top-level
bullets). `phase_level: 2` reveals at the first sub-bullet level instead — a top-level
bullet with sub-bullets appears alongside its first sub-bullet, and a top-level bullet
with no sub-bullets at all just becomes its own step.

`phase_in` works on other layouts too:

- **`stacked`** — reveals the body's bullets exactly as above (`phase_level` included).
  The `formula` box stays visible on every step.
- **`split`** — reveals one panel per step. Earlier panels dim, and panels not shown yet
  keep their space so nothing shifts. A final step shows every panel at full brightness:
  3 panels → 4 steps.
- **`image`** — cycles through `phase_images` full-bleed, one per step, in place of the
  single `image` field. There's no extra final step: 3 images → 3 steps. `title`/`kicker`
  stay as the caption throughout.

```markdown
---
layout: image
title: Time Series
phase_in: true
phase_images:
  - image: images/t0.png
    alt: Frame at t = 0
  - image: images/t1.png
    alt: Frame at t = 1
---
```

### Citations & references

Set `bibliography:` in `deck.yaml` to a file of numbered references — a `.bib` file
(BibTeX, formatted per the American Chemical Society/ACS style — the only style
implemented so far) or a plain file of `"key": "citation text"` lines:

```yaml
bibliography: refs.bib   # or refs.md -- see below
```

Cite from a slide's body with `[@key]`, or several at once with `[@key1; @key2]`:

```markdown
The reaction proceeds via a radical mechanism [@smith2020].
```

References are numbered in the order they're first cited across the whole deck (not
per-slide), rendered inline as a small superscript `[1]` (linking to the paper's DOI
when the bibliography entry has one), collected as a small footnote at the bottom-left
of whichever slide cited them, and listed in full wherever you place a `layout:
references` slide, typically the last one.

Cite from an image instead of body text with `reference: key` (`images[]`/`panels[]`
entries) or `image_reference: key` (the single boxed `image`, or the full-bleed `image`
layout's image) — its assigned number appears as a small badge in the image's top-right
corner.

**BibTeX (`.bib`) files**: a deliberately partial parser, not the full BibTeX spec —
`article`, `book`, `incollection`/`inbook`, and `inproceedings` entries are recognized
and ACS-formatted; anything else falls back to whatever of author/title/year is present.
Not supported: `@string` macros, cross-references, and LaTeX accent/escape sequences
(`{\'e}` stays literal) — write accented characters directly as UTF-8 instead. Journal
names are used exactly as given, with no abbreviation lookup.

**Plain (`.md`) files**: one entry per line, the citation text used exactly as given
(including any HTML you write yourself, e.g. `<i>...</i>`) with an optional DOI as a
third field:

```text
"smith2020": "Smith, J. A.; Doe, J. B. A Study of DNA Nanotechnology. J. Chem. 2020, 12, 34-56." : "10.1021/xyz123"
"jones2019": "Jones, A. Principles of Organic Synthesis. Academic Press: New York, 2019."
```

Citing a key that isn't in the bibliography, or citing anything at all with no
`bibliography:` configured, is a build error — without `bibliography:` set, `[@...]`-
shaped text is otherwise left completely untouched.

On a `phase_in` slide, the footnote list only shows references for whichever bullet,
panel or image is *currently* revealed at each step — not the whole slide's accumulated
citations — with the final "everything undimmed" step (if the layout has one) showing
the full combined list.

### PDFs as images

Any image-path field (`image`, `background`, `images[].image`, `panels[].image`,
`phase_images[].image`) accepts a `.pdf` file too — no different syntax, just point at
a PDF the way you'd point at a PNG. Its first page is rasterized to a PNG at build time
(200 DPI, not configurable) and flows through the rest of the pipeline exactly like any
other image — same styling, same click-to-zoom, same two-image aspect-ratio
arrangement, same citation reference badges. This needs the `pdf-images` extra:

```bash
uv sync --extra pdf-images
```

A PDF referenced on multiple slides is only rasterized once. Only the first page is
used; there's currently no way to pick a different page.

### Placeholder images

Any `image` (on `content` or `image` layouts), `background`, or `images`/`panels` entry
accepts a LaTeX-`mwe`-style placeholder name instead of a real file path — no image asset
needed while drafting: `example-image` (a plain outlined box) or `example-image-a`
through `example-image-z` (the same box with that letter in it, e.g. `example-image-c`).
These are bundled with the package and copied into the build like any other referenced
image. Omitted `alt` text is auto-filled (e.g. "Placeholder image C"), so no warning
fires for a placeholder left without one.

### Deck-wide config (optional)

A `deck.yaml` file next to your `.md` file (or passed via `--config`) sets page-wide
defaults:

```yaml
title: My Presentation      # <title> tag
default_author: Jane Doe    # used when a title slide omits `author`
theme: alomancy              # named preset — see below
bibliography: refs.bib       # numbered citations — see Citations & references above
```

`theme:` accepts either of two forms:

- **A named preset** (a single string) — swaps colors, the body font, and an optional
  watermark image in one line. Shipped presets:

  | Preset | Look |
  |---|---|
  | `default` | The original dark/gold theme (used automatically if `theme:` is omitted — no visual change either way) |
  | `alomancy` | Dark, with ALomancy's brand violet (`#6C2FBE`) as the accent, the "Inter" font, and a subtle ALomancy logo watermark in the bottom-left corner of every slide |
  | `neuefische` | Dark violet background with Neuefische's brand orange (`#f44717`) as the accent, the "Poppins" font, and a subtle Neuefische logo watermark |
  | `fhi` | Light background with dark teal body text/panels, an olive-green (`#a5b631`) accent, the "Poppins" font, and a subtle FHI logo watermark — the one light-background preset, so its title slide overrides `title-fg` (see below) to stay legible |

  New presets are added by registering a `ThemeDefinition` in `slide_maker/themes.py` — see
  that module for the fields (`colors`, `font_body`, `watermark`).

- **A raw dict of CSS custom-property overrides** (the original form, still fully
  supported) — layers only the keys you set on top of `assets/style.css`'s own defaults,
  independent of any preset:
  ```yaml
  theme:
    accent: "#4cc9f0"
  ```
  Overridable keys: `bg`, `bg-panel`, `fg`, `fg-muted`, `accent`, `accent-dim`, `border`,
  and `title-fg` — the title slide's `h1`/`subtitle`/author-date text color, which
  defaults to `fg` and only needs setting if `fg` doesn't contrast against the title
  slide's translucent dark panel (a fixed color, independent of the theme) — e.g. a
  light-background theme with a dark `fg`, like `fhi` above, which sets it to white.

## CLI

```
slides_md <input.md>          # build into build/ next to input, then serve it
  [--force]                   # overwrite a non-empty output directory (needed to rebuild)
  [-o DIR]                    # output directory instead of build/ next to input
  [--port N]                  # default: 8000
```

`slides_md` is the quick preview shortcut; for every other option use the full command:

```
python -m slide_maker build <input.md> -o <output_dir>
  [--config deck.yaml]        # default: deck.yaml next to input, if present
  [--images-dir DIR]          # default: input file's directory
  [--strict]                  # promote warnings (missing image_alt, unknown fields, etc.) to errors
  [--force]                   # overwrite a non-empty output directory
  [--serve]                   # serve the output with `python3 -m http.server` after building
  [--pdf PATH]                # also export a PDF (one page per slide) to PATH, via headless Chromium
  [--thumbnail PATH]          # also export a PNG screenshot of the title slide to PATH
```

Only images actually referenced by a slide are copied into `<output>/slide_images/`.
A missing referenced image is always a build error, `--strict` or not. A `.pdf` file
can be used anywhere a PNG/JPEG can — its first page is rasterized (200 DPI) and
treated identically from there on — with the `pdf-images` extra (`uv sync --extra
pdf-images`).

`--pdf` and `--thumbnail` both require the `pdf` extra (`uv sync --extra pdf`) plus
a one-time `uv run playwright install chromium` to download the browser.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
```

CI (`.github/workflows/ci.yml`) runs tests (Python 3.10-3.12), `ruff check`, and a docs
build with warnings promoted to errors on every push/PR — see `docs/contributing.md` for
details.

`examples/demo/slides.md` exercises all six layouts, background alpha, citations, and
KaTeX — useful as both a smoke test and a syntax reference.

`docs/_static/cheatsheet.pdf` (the downloadable cheatsheet linked from the docs site) is
generated from `examples/cheatsheet/slides.md` by `scripts/build_cheatsheet.py` — a
dev-only script needing the `pdf` extra, same as `--pdf`/`--thumbnail`. Re-run it and
commit the result whenever that source deck changes:

```bash
python scripts/build_cheatsheet.py
```
