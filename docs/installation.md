# Installation

## Installing slide_maker

There's no PyPI package yet, so install from source:

```bash
git clone https://github.com/julianholland/slides_md.git
cd slide_maker
pip install -e .
```

(The GitHub repository is named `slides_md`; the local directory and Python package are
named `slide_maker`/`slide-maker` — clone into whatever directory name you like, just
`cd` into it before running `pip install`.)

This installs the `slide-maker` console script and enables `python -m slide_maker`.
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
pip install -e ".[dev]"
pytest
```

## Building these docs locally

```bash
pip install -e ".[docs]"
cd docs
make html
```

## PDF export

`--pdf` (see `docs/cli.md`) renders the deck via headless Chromium, so it needs its own
extra plus a one-time browser download:

```bash
pip install -e ".[pdf]"
playwright install chromium
```

Then open `docs/_build/html/index.html` in a browser. This step also regenerates the
live demo decks used by the {doc}`layout-gallery` page automatically — no separate
command needed.
