# slide_maker

[![CI](https://github.com/julianholland/slides_md/actions/workflows/ci.yml/badge.svg)](https://github.com/julianholland/slides_md/actions/workflows/ci.yml)

Turn a single Markdown file into a static HTML slide deck. No client-side framework —
just the same vanilla HTML/CSS/JS approach as the hand-built [`sulfur_slides`](../sulfur_slides)
deck it's based on: a dark theme, keyboard/click navigation, click-to-zoom images, and
vendored KaTeX for math, with no build step or CDN dependency in the output.

## Quickstart

```bash
pip install -e .
python -m slide_maker build examples/demo/slides.md -o build/demo --serve
```

This builds `build/demo/index.html` (plus `assets/`, `vendor/katex/`, and
`slide_images/`) and serves it at `http://localhost:8000`.

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
matching the KaTeX formula box style). Don't use Markdown headings or `![]()` images in
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

### Per-slide fields

| field | applies to | notes |
|---|---|---|
| `layout` | all | `title` / `content` / `stacked` / `split` / `image`; default `content` |
| `title` | all | required for `title` layout; optional caption for `image` |
| `kicker` | content/stacked/split/image | small uppercase label above the title |
| `subtitle` | title | |
| `author` | title | falls back to `deck.yaml`'s `default_author` |
| `date` | title | literal string, or `today` to fill in the build date |
| `image` / `image_alt` / `image_label` | content, image | on `content`, a boxed image with an optional caption `image_label` (mutually exclusive with `video`/`panels`/`images`); on `image`, the full-bleed slide image (required, mutually exclusive with `background`). Accepts a placeholder name (see below) in place of a real path |
| `images` | content | exactly 2 `{image, label?, alt?}`; auto-arranged stacked or side-by-side from aspect ratio (mutually exclusive with `image`/`video`/`panels`) |
| `video` | content | mutually exclusive with `image`/`panels`/`images` |
| `panels` | content, split | list of `{image, label, alt?}`; required for `split` |
| `background` | all except `image` | image path; layers behind the slide content |
| `background_opacity` | all | `0.0`-`1.0`, default `1.0` |
| `fit` | image | `contain` (default, fit to screen) or `cover` (fill the screen) |
| `formula` | content/stacked | raw LaTeX (no `$$`), rendered in a `.formula-box` |
| `formula_note` | content/stacked | small caption under the formula |
| `notes` | all | speaker notes, emitted as an HTML comment (not visible) |
| `id` / `classes` | all | override the slide's `id`, or add extra CSS classes |

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
```

`theme:` accepts either of two forms:

- **A named preset** (a single string) — swaps colors, the body font, and an optional
  watermark image in one line. Shipped presets:

  | Preset | Look |
  |---|---|
  | `default` | The original dark/gold theme (used automatically if `theme:` is omitted — no visual change either way) |
  | `alomancy` | Dark, with ALomancy's brand violet (`#6C2FBE`) as the accent, the "Inter" font, and a subtle ALomancy logo watermark in the bottom-left corner of every slide |

  New presets are added by registering a `ThemeDefinition` in `slide_maker/themes.py` — see
  that module for the fields (`colors`, `font_body`, `watermark`).

- **A raw dict of CSS custom-property overrides** (the original form, still fully
  supported) — layers only the keys you set on top of `assets/style.css`'s own defaults,
  independent of any preset:
  ```yaml
  theme:
    accent: "#4cc9f0"
  ```
  Overridable keys: `bg`, `bg-panel`, `fg`, `fg-muted`, `accent`, `accent-dim`, `border`.

## CLI

```
python -m slide_maker build <input.md> -o <output_dir>
  [--config deck.yaml]        # default: deck.yaml next to input, if present
  [--images-dir DIR]          # default: input file's directory
  [--strict]                  # promote warnings (missing image_alt, unknown fields, etc.) to errors
  [--force]                   # overwrite a non-empty output directory
  [--serve]                   # serve the output with `python3 -m http.server` after building
  [--pdf PATH]                # also export a PDF (one page per slide) to PATH, via headless Chromium
```

Only images actually referenced by a slide are copied into `<output>/slide_images/`.
A missing referenced image is always a build error, `--strict` or not.

`--pdf` requires the `pdf` extra (`pip install -e ".[pdf]"`) plus a one-time
`playwright install chromium` to download the browser.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

CI (`.github/workflows/ci.yml`) runs tests (Python 3.10-3.12), `ruff check`, and a docs
build with warnings promoted to errors on every push/PR — see `docs/contributing.md` for
details.

`examples/demo/slides.md` exercises all five layouts, background alpha, and KaTeX —
useful as both a smoke test and a syntax reference.
