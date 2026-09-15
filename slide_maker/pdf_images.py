"""Rasterize a PDF's first page to a PNG so it can be used anywhere a PNG/JPEG image
path is already accepted (`ImageResolver.resolve` routes any `.pdf` source through
`rasterize_pdf` before its normal basename/collision handling — see build.py).

Uses PyMuPDF (`fitz`), a dev/runtime-optional extra (`pip install -e ".[pdf-images]"`)
kept out of the 3 core runtime dependencies the same way `pdf`'s Playwright is.
"""

from __future__ import annotations

from pathlib import Path

from .parser import SlideMakerError


def rasterize_pdf(pdf_path: Path, out_dir: Path, *, dpi: int = 200, slide_index: int | None = None) -> Path:
    try:
        import pymupdf  # PyMuPDF -- `import fitz` is the same library under its old, deprecated name
    except ImportError as exc:
        raise SlideMakerError(
            "using a PDF as an image requires the 'pdf-images' extra: pip install -e '.[pdf-images]'",
            slide_index=slide_index,
        ) from exc

    try:
        doc = pymupdf.open(pdf_path)
    except Exception as exc:
        raise SlideMakerError(f"could not open PDF '{pdf_path}': {exc}", slide_index=slide_index) from exc

    try:
        if doc.page_count == 0:
            raise SlideMakerError(f"PDF has no pages: {pdf_path}", slide_index=slide_index)
        # A PDF's native unit is 1/72 inch, so dpi/72 is the standard zoom factor to
        # render at a given DPI.
        zoom = dpi / 72
        pixmap = doc.load_page(0).get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{pdf_path.stem}.png"
        pixmap.save(out_path)
    finally:
        doc.close()

    return out_path
