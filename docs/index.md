# slide_maker Documentation

Welcome to slide_maker — turn a single Markdown file into a static HTML slide deck.

```{toctree}
:maxdepth: 2
:caption: Contents:

installation
quickstart
authoring-guide
layout-gallery
cli
api/index
contributing
```

## Overview

slide_maker takes one Markdown file with YAML frontmatter per slide and renders it to
plain HTML/CSS/JS — no client-side framework, no build step, no CDN dependency in the
output. It's the same vanilla approach as the hand-built `sulfur_slides` deck it's
modeled on: a dark theme, keyboard/click navigation, click-to-zoom images, and vendored
KaTeX for math.

## Key Features

- Five slide layouts (`title`, `content`, `stacked`, `split`, `image`) — see the
  {doc}`layout-gallery` for a live example of each
- Named color/font/watermark themes, switchable with a single `theme:` line in
  `deck.yaml`
- Two-image pairs auto-arranged (stacked vs. side-by-side) from real pixel aspect ratio
- Click-to-zoom image lightbox and vendored KaTeX — no network requests in the built
  output
- Only three runtime dependencies (PyYAML, markdown-it-py, Jinja2) — no Pillow, hand-
  parsed image headers instead

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
