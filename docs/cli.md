# CLI Reference

```
slides_md <input.md>          # build into build/ next to input, then serve it
  [--force]                   # overwrite a non-empty output directory (needed to rebuild)
  [-o DIR]                    # output directory instead of build/ next to input
  [--port N]                  # default: 8000
```

`slides_md` is the quick preview shortcut; for every other option use the full command:

```
python -m deckoction build <input.md> -o <output_dir>
  [--config deck.yaml]        # default: deck.yaml next to input, if present
  [--images-dir DIR]          # default: input file's directory
  [--strict]                  # promote warnings (missing image_alt, unknown fields, etc.) to errors
  [--force]                   # overwrite a non-empty output directory
  [--serve]                   # serve the output with `python3 -m http.server` after building
  [--pdf PATH]                # also export a PDF (one page per slide) to PATH
  [--thumbnail PATH]          # also export a PNG screenshot of the title slide to PATH
```

The same command is also available as the `deckoction` console script:

```bash
deckoction build slides.md -o build/mydeck
```

Only images actually referenced by a slide are copied into `<output>/slide_images/`.
A missing referenced image is always a build error, `--strict` or not.

`--serve` shells out to `python3 -m http.server` in the output directory after a
successful build, and blocks until you stop it (`Ctrl+C`).

`--pdf` renders one PDF page per slide via headless Chromium, using the built HTML
output as the source (so it runs after the build, before `--serve`). It requires the
`pdf` extra: `uv sync --extra pdf` followed by a one-time `uv run playwright install
chromium` to download the browser binary.

`--thumbnail` screenshots the deck's initial view (slide 1 — the deck always opens
there) at a 1600x900 viewport, using the same local-serving approach and the same
`pdf` extra as `--pdf`. Runs after the build and after `--pdf`, before `--serve`.
