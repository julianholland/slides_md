# slide_maker

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
| `image` / `image_alt` / `image_label` | content, image | on `content`, a boxed image with an optional caption `image_label` (mutually exclusive with `video`/`panels`/`images`); on `image`, the full-bleed slide image (required, mutually exclusive with `background`) |
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

### Deck-wide config (optional)

A `deck.yaml` file next to your `.md` file (or passed via `--config`) sets page-wide
defaults:

```yaml
title: My Presentation      # <title> tag
default_author: Jane Doe    # used when a title slide omits `author`
theme:                      # optional CSS custom-property overrides
  accent: "#4cc9f0"
```

## CLI

```
python -m slide_maker build <input.md> -o <output_dir>
  [--config deck.yaml]        # default: deck.yaml next to input, if present
  [--images-dir DIR]          # default: input file's directory
  [--strict]                  # promote warnings (missing image_alt, unknown fields, etc.) to errors
  [--force]                   # overwrite a non-empty output directory
  [--serve]                   # serve the output with `python3 -m http.server` after building
```

Only images actually referenced by a slide are copied into `<output>/slide_images/`.
A missing referenced image is always a build error, `--strict` or not.

## Development

```bash
pip install -e ".[dev]"
pytest
```

`examples/demo/slides.md` exercises all five layouts, background alpha, and KaTeX —
useful as both a smoke test and a syntax reference.
