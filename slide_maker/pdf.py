from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .parser import SlideMakerError

# rem is always relative to the root <html> font-size, so there's no per-slide CSS knob to
# shrink one overflowing slide's type scale without affecting every other slide too. A CSS
# `transform: scale()` was tried instead, but transforms only affect paint, not layout — Chromium's
# print paginator fragments a `.slide` based on its *unscaled* layout height, so an overflowing
# slide got its content fragmented and re-painted (visibly overlapping) across the forced page
# break instead of actually shrinking. So this scales real `font-size` on each element that sets
# an explicit rem-based size in assets/style.css (a genuine layout change, so scrollHeight actually
# drops and no fragmentation happens) — every other rem/em size in the stylesheet (paddings, KaTeX's
# own internal em-based sizing) is relative to one of these, so scaling just the anchors cascades
# correctly without needing to touch every descendant individually.
#
# Deliberately no minimum-scale floor: testing showed that if a slide *still* overflows its page
# after shrinking (an extreme floor would allow), Chromium's print pagination doesn't just clip
# the remainder — it duplicates/overlaps a fragment of the content on the page instead. Always
# shrinking to an exact fit avoids that pagination bug entirely; a pathological slide (tens of
# bullets) ends up with small but correctly non-overlapping text instead.
_TEXT_SELECTOR = "h1, h2.kicker, ul.bullets, blockquote, .formula-box, .formula-note, .panel-label, .meta, .subtitle"
_FIT_JS = f"""
() => {{
  document.querySelectorAll('.slide').forEach((slide) => {{
    const content = slide.querySelector('.slide-content');
    if (!content) return;
    const availH = content.clientHeight;
    const availW = content.clientWidth;
    const neededH = content.scrollHeight;
    const neededW = content.scrollWidth;
    if (neededH <= availH && neededW <= availW) return;
    const scale = Math.min(1, availH / neededH, availW / neededW);
    content.querySelectorAll('{_TEXT_SELECTOR}').forEach((el) => {{
      const currentPx = parseFloat(getComputedStyle(el).fontSize);
      el.style.fontSize = `${{currentPx * scale}}px`;
    }});
  }});
}}
"""


def export_pdf(output_dir: Path, pdf_path: Path) -> None:
    """Render a built deck (`output_dir/index.html`) to a PDF, one page per slide.

    Serves `output_dir` over a throwaway local HTTP server and drives headless
    Chromium (via Playwright) to print it, relying on the `@media print` rules in
    assets/style.css to stack every slide as its own page.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SlideMakerError(
            "PDF export requires the 'pdf' extra: "
            "pip install -e '.[pdf]' && playwright install chromium"
        ) from exc

    handler = partial(SimpleHTTPRequestHandler, directory=str(output_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    port = server.server_address[1]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle")
                page.emulate_media(media="print")
                page.evaluate(_FIT_JS)
                pdf_path.parent.mkdir(parents=True, exist_ok=True)
                page.pdf(path=str(pdf_path), print_background=True, prefer_css_page_size=True)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server_thread.join()
