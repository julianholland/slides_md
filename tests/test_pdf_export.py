import functools
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from slide_maker.build import build
from slide_maker.pdf import _FIT_JS, export_pdf

DEMO_DIR = Path(__file__).resolve().parents[1] / "examples" / "demo"

playwright_sync_api = pytest.importorskip("playwright.sync_api")


def _chromium_available() -> bool:
    try:
        with playwright_sync_api.sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _chromium_available(), reason="Playwright Chromium browser is not installed"
)


def test_export_pdf_page_per_slide(tmp_path):
    pypdf = pytest.importorskip("pypdf")

    out = tmp_path / "out"
    result = build(input_path=DEMO_DIR / "slides.md", output_dir=out)

    pdf_path = tmp_path / "demo.pdf"
    export_pdf(out, pdf_path)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) == result.slide_count


def test_auto_fit_shrinks_overlong_slide(tmp_path):
    pypdf = pytest.importorskip("pypdf")

    fixture = tmp_path / "overlong.md"
    bullets = "\n".join(
        f"- Bullet point number {i} with a decently long sentence to pad things out a bit"
        for i in range(1, 10)
    )
    fixture.write_text(
        "---\nlayout: content\nkicker: Overflow test\ntitle: Slightly Too Much Content\n---\n\n"
        f"{bullets}\n"
    )

    out = tmp_path / "out"
    build(input_path=fixture, output_dir=out)

    pdf_path = tmp_path / "overlong.pdf"
    export_pdf(out, pdf_path)

    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) == 1

    # export_pdf's own browser session is already closed by the time it returns, so
    # independently re-run the same fit pass here to confirm the overlong slide's content
    # actually fits its page (rather than trusting page count alone, which would also be 1
    # for a slide that silently got clipped or corrupted by print-pagination overlap).
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(out))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with playwright_sync_api.sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            port = server.server_address[1]
            page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle")
            page.emulate_media(media="print")
            page.evaluate(_FIT_JS)
            overflows = page.eval_on_selector(
                ".slide-content",
                "e => e.scrollHeight > e.clientHeight || e.scrollWidth > e.clientWidth",
            )
            browser.close()
    finally:
        server.shutdown()
        thread.join()

    assert overflows is False
