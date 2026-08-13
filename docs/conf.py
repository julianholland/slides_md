"""Sphinx configuration for slide_maker documentation."""

import sys
from pathlib import Path

# slide_maker's package lives at the repo root (no src/ layout).
sys.path.insert(0, str(Path(__file__).parent.parent))
# So `import _demo_build` below (and Sphinx's own config loading) can find it.
sys.path.insert(0, str(Path(__file__).parent))

# Project information
project = "slide_maker"
copyright = "2026, Julian Holland"
author = "Julian Holland"
release = "0.1.0"

# Extensions
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "myst_parser",  # For markdown support
]

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# Autosummary settings
autosummary_generate = True

# Source files
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Master document
master_doc = "index"

# docs/demo/*/slides.md are slide_maker deck *source* files (consumed by
# _demo_build.py), not documentation pages -- keep Sphinx from trying to
# parse them as content.
exclude_patterns = ["_build", "demo"]

# HTML theme
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_theme_options = {
    "logo_only": False,
}

html_context = {
    "display_github": True,
    "github_user": "julianholland",
    "github_repo": "slides_md",
    "github_version": "master",
    "conf_py_path": "/docs/",
}

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
}

# Build the layout-gallery demo decks (docs/demo/*) into _static/demo/ so
# layout-gallery.md can embed them via <iframe>. Runs at import time, before
# Sphinx copies html_static_path, so the generated HTML exists on disk in
# time to be included in the build output — works identically for `make
# html` locally and on Read the Docs, no custom build hook needed.
from _demo_build import build_all_demo_decks  # noqa: E402

build_all_demo_decks()
