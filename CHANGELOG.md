# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `images` accepts 2 or more images (was exactly 2). They're arranged into rows in
  reading order, picking the row layout that leaves the least blank space while keeping
  the images roughly the same size.
- A `phase_images` entry on a `content` slide can now be an `images` group
  (`- images: [{image: ...}, {image: ...}, ...]`) shown together on that reveal step,
  arranged like the `images` field.
- `subtitle` now works on every layout, not just `title`: it renders as a line under the
  title (inside the caption overlay on `image`). Previously it was silently ignored on
  other layouts.

### Changed
- Two-image `images` now use the same row search, which assumes the real (wider than
  square) media column; some pairs that used to stack now sit side by side or vice versa.
  The `.image-pair`/`.image-pair-item` CSS classes are replaced by `.image-grid`,
  `.image-grid-row` and `.image-grid-item`.

### Fixed
- A `phase_images` entry without an `image` field now gives a clear error instead of
  crashing with `KeyError: 'image'`.

## [0.2.1] - 2026-10-05

### Added
- `deckoction slides.md` now builds next to the input and serves it, exactly like
  `slides_md slides.md` (same `-o`/`--force`/`--port` options). `deckoction build ...` is
  unchanged.

## [0.2.0] - 2026-10-05

### Changed
- **Breaking:** the import package is renamed from `slide_maker` to `deckoction`, matching
  the PyPI name. Update `import slide_maker` / `python -m slide_maker` to `deckoction`.
- **Breaking:** the `slide-maker` command is renamed to `deckoction` (e.g.
  `deckoction build slides.md -o build/deck`). The `slides_md` shortcut is unchanged.

## [0.1.1] - 2026-10-05

First release on PyPI as `Deckoction-md`. (The `v0.1.0` tag predates the rename from
`slides-md`, which PyPI rejected as too similar to an existing project; it was never published.)

### Added
- **Markdown → static HTML slide decks**: one `slides.md` file, slides separated by `+++`,
  each with YAML frontmatter; output is plain HTML/CSS/vanilla JS with vendored KaTeX (no CDN).
- **Six layouts**: `title`, `content`, `stacked`, `split`, `image`, `references`.
- Background images with adjustable opacity on any layout; full-bleed `image` layout with
  `fit: contain|cover`.
- Two-image pairs that pick a side-by-side or stacked arrangement from the images' aspect
  ratios; click-to-zoom lightbox.
- LaTeX `mwe`-style placeholder images (`example-image`, `example-image-a`..`-z`) and PDFs
  usable anywhere an image path is accepted (`pdf-images` extra).
- **Phase-in reveal** (`phase_in: true`) for `content`, `stacked`, `split` and `image` slides.
- **Citations**: `[@key]` in slide bodies and `reference` on images, from a BibTeX or plain
  bibliography, with per-slide footnotes and a `references` layout.
- **Themes** (`deck.yaml` `theme:` presets or free-form CSS overrides), GFM pipe tables,
  blockquotes, `<!-- -->` comments (including commenting out whole slides).
- **PDF and thumbnail export** (`--pdf`, `--thumbnail`; `pdf` extra) via headless Chromium,
  with auto-shrink of overflowing slides.
- `slides_md` shortcut command: build next to the input and serve at :8000.

### Changed
- Packaging moved to uv + hatchling: `uv.lock` committed, dev tools in a PEP 735 `dev`
  dependency group, version taken from git tags (`hatch-vcs`). Distribution renamed from
  `slide-maker` to `Deckoction-md`; the import package (`slide_maker`) and the `slide-maker` /
  `slides_md` commands are unchanged.
