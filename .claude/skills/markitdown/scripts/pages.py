#!/usr/bin/env python3
"""
pages.py — render PDF pages to PNG images so the agent can *look* at them.

OCR (`convert.py` / `ocr.py`) recovers printed text, but diagrams, charts,
stamps, signatures, handwriting, and photos only make sense visually. This
tool renders the requested pages to PNG files; the agent then opens them with
the Read tool, which displays images natively.

Standalone image files (.png/.jpg/...) don't need this — Read them directly.

Usage:
    python pages.py doc.pdf                  # page 1
    python pages.py doc.pdf --pages 3        # page 3
    python pages.py doc.pdf --pages 2-5,8    # pages 2,3,4,5 and 8
    python pages.py doc.pdf --pages all
    python pages.py doc.pdf --pages 1 --dpi 200 --out ./imgs

Prints one output path per line; nothing else, so it is cheap to run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_OUT = Path(".markitdown") / "pages"
MAX_PAGES_DEFAULT = 20  # refuse to silently render a 500-page book


def parse_pages(spec: str, total: int) -> list[int]:
    """'1', '2-5,8', 'all' -> sorted list of valid 1-based page numbers."""
    if spec.strip().lower() == "all":
        return list(range(1, total + 1))
    picked: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            picked.update(range(int(a), int(b) + 1))
        else:
            picked.add(int(part))
    return sorted(p for p in picked if 1 <= p <= total)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Render PDF pages to PNG for visual inspection.")
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="1",
                    help="page spec: '1', '2-5,8', 'all' (default: 1)")
    ap.add_argument("--dpi", type=int, default=150,
                    help="render resolution (default: 150; 200+ for fine detail)")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help=f"output dir (default: {DEFAULT_OUT})")
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES_DEFAULT,
                    help=f"safety cap per run (default: {MAX_PAGES_DEFAULT})")
    args = ap.parse_args(argv)

    src = Path(args.pdf)
    if not src.is_file():
        print(f"error: {src} not found", file=sys.stderr)
        return 1
    if src.suffix.lower() != ".pdf":
        print(f"{src} is not a PDF — open image files directly with the Read tool.",
              file=sys.stderr)
        return 1

    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(src))
    try:
        total = len(pdf)
        pages = parse_pages(args.pages, total)
        if not pages:
            print(f"error: no valid pages in '{args.pages}' (document has {total})",
                  file=sys.stderr)
            return 1
        if len(pages) > args.max_pages:
            print(f"note: {len(pages)} pages requested, rendering first "
                  f"{args.max_pages} (raise --max-pages to override)",
                  file=sys.stderr)
            pages = pages[: args.max_pages]

        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        scale = max(args.dpi, 72) / 72.0

        for n in pages:
            bitmap = pdf[n - 1].render(scale=scale)
            pil = bitmap.to_pil()
            try:
                out = out_dir / f"{src.stem}_p{n}.png"
                pil.save(out)
            finally:
                pil.close()
            print(out)
        return 0
    finally:
        pdf.close()


if __name__ == "__main__":
    raise SystemExit(main())
