# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
