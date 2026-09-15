#!/usr/bin/env python3
"""One-off generator for the downloadable feature cheatsheet PDF.

Dev-only tool (not part of the installed package, not a runtime dependency — requires
the `pdf` extra, same as `slide_maker.pdf.export_pdf`: `pip install -e ".[pdf]"` plus a
one-time `playwright install chromium`). Builds `examples/cheatsheet/slides.md` into a
throwaway directory and exports it to `docs/_static/cheatsheet.pdf`, one page per slide.
Run this again and re-commit the output whenever the cheatsheet deck changes:

    python3 scripts/build_cheatsheet.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from slide_maker.build import build
from slide_maker.pdf import export_pdf

ROOT = Path(__file__).resolve().parent.parent
SLIDES = ROOT / "examples" / "cheatsheet" / "slides.md"
OUT_PDF = ROOT / "docs" / "_static" / "cheatsheet.pdf"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "cheatsheet"
        build(input_path=SLIDES, output_dir=out_dir, strict=True)
        OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
        export_pdf(out_dir, OUT_PDF)
    print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
