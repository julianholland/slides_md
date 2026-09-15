# Contributing

```bash
pip install -e ".[dev]"
pytest
pytest tests/test_build_end_to_end.py::test_build_demo_deck   # run a single test
ruff check .
```

Ruff is configured in `pyproject.toml`'s `[tool.ruff]` (pyflakes + import ordering — a
modest baseline, not a full style/type-annotation ruleset). No formatter is configured.

## CI

`.github/workflows/ci.yml` runs on every push and pull request:

- **test** — `pytest`, matrixed across Python 3.10, 3.11, 3.12
- **lint** — `ruff check .`
- **docs** — `sphinx-build -W` (a docs build with any warning promoted to a hard error)

Read the Docs builds separately from this CI (tolerating warnings, per
`.readthedocs.yaml`'s `fail_on_warning: false`) — the `docs` CI job is a stricter local
gate that catches doc breakage before it ever reaches RTD.

`examples/demo/slides.md` exercises all six layouts, background alpha, image pairs,
citations, and KaTeX in one deck, and doubles as the primary integration-test fixture
(`tests/test_build_end_to_end.py`) — keep it in sync when adding fields/layouts.

## How it fits together

The build pipeline (`slide_maker/build.py:build`): read `slides.md` (+ optional
`deck.yaml`) → split on `+++` (`parser.py`) → validate per-slide YAML frontmatter
(`schema.py`) → render Markdown body + LaTeX (`render.py`) → render each slide via its
layout's Jinja template (`layouts.py` maps layout name → template) → assemble
`base.html.jinja` → write `index.html`, copy `assets/` and `vendor/katex/` verbatim, copy
only the images actually referenced into `<output>/slide_images/`.

For the full internals reference (why block math is a separate `formula` field, the
two-image aspect-ratio heuristic, the click-to-zoom lightbox implementation, and so on),
see `CLAUDE.md` at the repository root — it's written for AI coding agents working in
this codebase, but is equally useful background for a human contributor.

### A known CSS trap, worth knowing before touching `base.html.jinja`/`style.css`

A `url()` value inside a CSS custom property resolves relative to the *stylesheet* that
consumes it via `var()` (`assets/style.css`, under `output/assets/`), not the HTML page
(`output/index.html`) — so any image path referencing `output/slide_images/` or
`output/assets/...` must be set as a literal inline `style="..."`/`src="..."` value
directly in a Jinja template, never routed through `var(--something)` inside
`assets/style.css`. This bit the `background`/full-bleed-image mechanism once already
(guarded by `tests/test_build_end_to_end.py::test_background_image_uses_inline_style_not_css_custom_property`)
and applies equally to the theme watermark image (guarded by
`tests/test_themes.py::test_watermark_src_is_inline_not_css_custom_property`).

### Themes

`slide_maker/themes.py` holds a small registry (`THEME_PRESETS`) of named
`ThemeDefinition`s (colors, a body font, and an optional watermark image), resolved by
`schema.build_deck_config` from `deck.yaml`'s `theme:` field — either a preset name
(`theme: alomancy`) or the original free-form dict of CSS overrides. See
{doc}`authoring-guide` for the user-facing docs, and `slide_maker/themes.py` itself for
adding a new preset (register a `ThemeDefinition`; no other file needs to change).
