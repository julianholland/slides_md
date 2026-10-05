# Installation

## Installing deckoction

Install the published package from PyPI (as a standalone CLI tool, via
[uv](https://docs.astral.sh/uv/)):

```bash
uv tool install deckoction-md                 # or: uv tool install 'deckoction-md[pdf]' for --pdf
```

or work from a source checkout:

```bash
git clone https://github.com/julianholland/slides_md.git
cd slides_md
uv sync
```

(The PyPI distribution is named `deckoction-md`; the importable Python package is
`deckoction`. In a checkout, prefix commands with `uv run`, e.g. `uv run slides_md ...`.)

This installs the `deckoction` and `slides_md` console scripts and enables `python -m deckoction`.
Requires Python 3.10 or later.

### Runtime dependencies

| Package | Version |
|---|---|
| [PyYAML](https://pyyaml.org/) | `>=6.0` |
| [markdown-it-py](https://github.com/executablebooks/markdown-it-py) | `>=3.0` |
| [Jinja2](https://jinja.palletsprojects.com/) | `>=3.1` |

That's the complete list — deliberately minimal (no Pillow; image dimensions are read by
hand-parsing PNG/JPEG/GIF headers instead).

### Running the test suite

```bash
uv sync
uv run pytest
```

## Building these docs locally

```bash
uv sync --extra docs
cd docs
uv run make html
```

## PDF export

`--pdf` (see `docs/cli.md`) renders the deck via headless Chromium, so it needs its own
extra plus a one-time browser download:

```bash
uv sync --extra pdf
uv run playwright install chromium
```

Then open `docs/_build/html/index.html` in a browser. This step also regenerates the
live demo decks used by the {doc}`layout-gallery` page automatically — no separate
command needed.
