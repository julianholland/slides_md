from __future__ import annotations

import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .parser import SlideMakerError


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
                thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(thumbnail_path))
            finally:
                browser.close()
    finally:
        server.shutdown()
        server_thread.join()
