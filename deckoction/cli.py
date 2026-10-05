from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .build import build, print_warnings
from .parser import SlideMakerError
from .pdf import export_pdf
from .thumbnail import export_thumbnail

SUBCOMMANDS = ("build",)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    # `deckoction slides.md` is the same as `slides_md slides.md` (build next to the input
    # and serve); only a leading subcommand or option goes to the subcommand parser below.
    if argv and argv[0] not in SUBCOMMANDS and not argv[0].startswith("-"):
        return serve_main(argv, prog="deckoction")

    parser = argparse.ArgumentParser(
        prog="deckoction",
        epilog="Shortcut: `deckoction slides.md [-o DIR] [--force] [--port N]` builds next to "
        "the input and serves it (same as `slides_md`).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build an HTML slide deck from a Markdown file")
    build_parser.add_argument("input", type=Path, help="Path to the slides.md file")
    build_parser.add_argument("-o", "--output", type=Path, required=True, help="Output directory")
    build_parser.add_argument("--config", type=Path, default=None, help="Path to deck.yaml (default: deck.yaml next to input)")
    build_parser.add_argument("--images-dir", type=Path, default=None, help="Base directory for resolving image paths (default: input file's directory)")
    build_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    build_parser.add_argument("--force", action="store_true", help="Overwrite a non-empty output directory")
    build_parser.add_argument("--serve", action="store_true", help="Serve the output directory with python3 -m http.server after building")
    build_parser.add_argument("--pdf", type=Path, default=None, help="Also export a PDF (one page per slide) to this path")
    build_parser.add_argument("--thumbnail", type=Path, default=None, help="Also export a PNG screenshot of the title slide to this path")

    args = parser.parse_args(argv)

    if args.command == "build":
        try:
            result = build(
                input_path=args.input,
                output_dir=args.output,
                config_path=args.config,
                images_dir=args.images_dir,
                strict=args.strict,
                force=args.force,
            )
        except SlideMakerError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        print_warnings(result.warnings)
        print(f"built {result.slide_count} slide(s) -> {result.output_dir}/index.html")

        if args.pdf:
            try:
                export_pdf(result.output_dir, args.pdf)
            except SlideMakerError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            print(f"exported PDF -> {args.pdf}")

        if args.thumbnail:
            try:
                export_thumbnail(result.output_dir, args.thumbnail)
            except SlideMakerError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            print(f"exported thumbnail -> {args.thumbnail}")

        if args.serve:
            subprocess.run(["python3", "-m", "http.server"], cwd=result.output_dir, check=False)

    return 0


def serve_main(argv: list[str] | None = None, prog: str = "slides_md") -> int:
    """`slides_md slides.md` — build into `<input dir>/build` and serve it."""
    parser = argparse.ArgumentParser(prog=prog, description="Build a slide deck and serve it for viewing")
    parser.add_argument("input", type=Path, help="Path to the slides.md file")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output directory (default: build/ next to input)")
    parser.add_argument("--force", action="store_true", help="Overwrite a non-empty output directory")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    args = parser.parse_args(argv)

    output = args.output or args.input.parent / "build"
    try:
        result = build(input_path=args.input, output_dir=output, force=args.force)
    except SlideMakerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print_warnings(result.warnings)
    print(f"built {result.slide_count} slide(s) -> {result.output_dir}/index.html")
    print(f"serving at http://localhost:{args.port}/ (Ctrl+C to stop)")
    try:
        subprocess.run([sys.executable, "-m", "http.server", str(args.port)], cwd=result.output_dir, check=False)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
