# CLI Reference

```
python -m slide_maker build <input.md> -o <output_dir>
  [--config deck.yaml]        # default: deck.yaml next to input, if present
  [--images-dir DIR]          # default: input file's directory
  [--strict]                  # promote warnings (missing image_alt, unknown fields, etc.) to errors
  [--force]                   # overwrite a non-empty output directory
  [--serve]                   # serve the output with `python3 -m http.server` after building
```

The same command is also available as the `slide-maker` console script:

```bash
slide-maker build slides.md -o build/mydeck
```

Only images actually referenced by a slide are copied into `<output>/slide_images/`.
A missing referenced image is always a build error, `--strict` or not.

`--serve` shells out to `python3 -m http.server` in the output directory after a
successful build, and blocks until you stop it (`Ctrl+C`).
