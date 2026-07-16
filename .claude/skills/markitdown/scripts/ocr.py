#!/usr/bin/env python3
"""
ocr.py — optional OCR helpers for the MarkItDown Skill.

MarkItDown extracts *embedded* text (real text PDFs, Office files, HTML).
It does **not** read pixels, so scanned PDFs and photos of text come back
empty. This module fills that gap with Tesseract:

* images  -> `pytesseract` reads the pixels directly.
* PDFs    -> `pypdfium2` (ships with markitdown[pdf]) renders each page to a
             bitmap, which `pytesseract` then OCRs.

Everything here is best-effort and import-guarded: if the tesseract binary or
`pytesseract` is missing, `ocr_available()` returns False and the caller
silently skips OCR instead of crashing.

Run directly for a quick check:
    python ocr.py <image-or-pdf> [--lang eng+rus] [--dpi 200]
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}


def ocr_available() -> bool:
    """True only if both the Python binding and the tesseract binary exist."""
    if shutil.which("tesseract") is None:
        return False
    try:
        import pytesseract  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def _installed_langs() -> set[str]:
    try:
        import pytesseract
        return set(pytesseract.get_languages(config=""))
    except Exception:  # noqa: BLE001
        return set()


def _resolve_lang(requested: str) -> str:
    """Drop languages tesseract does not have; never let a bad lang crash us."""
    installed = _installed_langs()
    if not installed:
        return requested  # can't introspect; let tesseract try and maybe fail
    wanted = [l for l in requested.split("+") if l in installed]
    if wanted:
        return "+".join(wanted)
    return "eng" if "eng" in installed else (sorted(installed)[0] if installed else "eng")


def ocr_image(path: Path, lang: str = "eng+rus") -> str:
    import pytesseract
    from PIL import Image

    lang = _resolve_lang(lang)
    with Image.open(path) as img:
        if img.mode not in ("L", "RGB"):
            img = img.convert("RGB")
        return pytesseract.image_to_string(img, lang=lang)


def ocr_pdf(path: Path, lang: str = "eng+rus", dpi: int = 200,
            max_pages: int = 0, jobs: int = 0) -> str:
    """Render each PDF page and OCR it. `max_pages=0` means all pages.

    Pages are OCRed in parallel: pytesseract shells out to the tesseract
    binary, so a thread pool gives near-linear speedup with CPU cores.
    Rendering stays sequential (pypdfium2 is not thread-safe) and is done
    in batches so a long document never holds every page bitmap in memory.
    """
    import os
    from concurrent.futures import ThreadPoolExecutor

    import pypdfium2 as pdfium
    import pytesseract

    lang = _resolve_lang(lang)
    scale = max(dpi, 72) / 72.0
    jobs = jobs or min(8, os.cpu_count() or 2)

    def _ocr_one(arg):
        idx, pil = arg
        try:
            return idx, pytesseract.image_to_string(pil, lang=lang).strip()
        finally:
            pil.close()

    chunks: dict[int, str] = {}
    pdf = pdfium.PdfDocument(str(path))
    try:
        n = len(pdf)
        if max_pages:
            n = min(n, max_pages)
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            for start in range(0, n, jobs):
                batch = []
                for i in range(start, min(start + jobs, n)):
                    batch.append((i, pdf[i].render(scale=scale).to_pil()))
                for idx, text in pool.map(_ocr_one, batch):
                    if text:
                        chunks[idx] = text
    finally:
        pdf.close()
    return "\n\n".join(f"<!-- page {i + 1} -->\n{chunks[i]}"
                       for i in sorted(chunks))


def ocr_file(path: Path, lang: str = "eng+rus", dpi: int = 200) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return ocr_pdf(path, lang=lang, dpi=dpi)
    if ext in IMAGE_EXTS:
        return ocr_image(path, lang=lang)
    return ""


def _main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="OCR an image or scanned PDF to text.")
    ap.add_argument("file")
    ap.add_argument("--lang", default="eng+rus")
    ap.add_argument("--dpi", type=int, default=200)
    args = ap.parse_args(argv)

    if not ocr_available():
        print("OCR unavailable: install tesseract + pytesseract "
              "(see scripts/setup.sh).", file=sys.stderr)
        return 3
    text = ocr_file(Path(args.file), lang=args.lang, dpi=args.dpi)
    sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
