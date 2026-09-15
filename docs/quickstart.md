# Quickstart

```bash
pip install -e .
python -m slide_maker build examples/demo/slides.md -o build/demo --serve
```

This builds `build/demo/index.html` (plus `assets/`, `vendor/katex/`, and
`slide_images/`) and serves it at `http://localhost:8000`.

`examples/demo/slides.md` (bundled with the repo) exercises all six layouts, background
alpha, an image pair, citations, and KaTeX in one deck — a good starting point to copy
from, and see
{doc}`layout-gallery` for a live, one-layout-at-a-time walkthrough.

## Writing your own deck

Create a `slides.md` with one or more `---`-fenced, YAML-frontmatter slides separated by
lines containing exactly `+++`:

```markdown
---
layout: title
title: My Presentation
subtitle: A subtitle
author: Jane Doe
date: today
---

+++

---
layout: content
kicker: Overview
title: Why a Markdown Slide Tool
image: diagram.png
image_alt: Diagram of the pipeline
---

- Author once in a single Markdown file
- Generator assembles static HTML/CSS/JS
```

Then build it:

```bash
python -m slide_maker build slides.md -o build/mydeck --serve
```

See {doc}`authoring-guide` for the full field reference and {doc}`cli` for every CLI
flag.
