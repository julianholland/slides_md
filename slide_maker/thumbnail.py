from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .parser import SlideMakerError

# `networkidle` only means every HTTP request finished -- every slide's <img> (and any
# slide's .bg-layer background-image) fetches regardless of which slide is .active
# (hidden elements still load their images), so a deck with many slides/images can
# reach networkidle while the *visible* slide's own image(s) are still decoding or
# compositing. This polls (via Playwright's wait_for_function) until the active
# slide's <img> tags AND its .bg-layer's CSS background-image (if any -- checked by
# racing a throwaway Image() probe against the browser's own cache, since there's no
# direct DOM API for "is this CSS background-image decoded") are all ready, so a heavy
# deck can't produce an incompletely-painted screenshot.
_WAIT_FOR_ACTIVE_SLIDE_PAINTED_JS = """
() => {
  const active = document.querySelector('.slide.active');
  if (!active) return true;
  const imgsReady = [...active.querySelectorAll('img')].every(
    (img) => img.complete && img.naturalHeight !== 0
  );
  if (!imgsReady) return false;
  const bg = active.querySelector('.bg-layer');
  if (!bg) return true;
  const match = bg.style.backgroundImage.match(/url\\(["']?(.*?)["']?\\)/);
  if (!match) return true;
  const probe = new Image();
  probe.src = match[1];
  return probe.complete && probe.naturalHeight !== 0;
}
"""


def export_thumbnail(
    output_dir: Path,
    thumbnail_path: Path,
    *,
    viewport: tuple[int, int] = (1600, 900),
) -> None:
    """Screenshot a built deck's first slide (`output_dir/index.html`) to a PNG.

    Serves `output_dir` over a throwaway local HTTP server and drives headless
    Chromium (via Playwright) to load it — `assets/script.js` always initializes
    on slide 1, so no navigation is needed before the screenshot.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SlideMakerError(
            "Thumbnail export requires the 'pdf' extra (it shares that extra's "
            "Playwright dependency): pip install -e '.[pdf]' && playwright install chromium"
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
                width, height = viewport
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle")
                page.wait_for_function(_WAIT_FOR_ACTIVE_SLIDE_PAINTED_JS)
                thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(thumbnail_path))
            finally:
                browser.close()
    finally:
        server.shutdown()
        server_thread.join()
