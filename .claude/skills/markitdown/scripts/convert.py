#!/usr/bin/env python3
"""
convert.py — MarkItDown Skill core converter.

Converts almost any document (PDF, Office, HTML, CSV/JSON/XML, EPUB, ZIP,
images, audio, ...) into clean Markdown, with an OCR fallback for scanned
PDFs and images.

Design goals
------------
* LOW TOKEN COST: by default the Markdown is written to a file and only a
  short manifest (path / size / word count / heading outline) is printed to
  stdout. The agent then reads the ``.md`` on demand with offset/limit
  instead of pulling a whole document into context.
* IDEMPOTENT: a file is only re-converted when its source changed (size +
  mtime are cached in ``.markitdown/manifest.json``). Repeated runs are cheap.
* GRACEFUL DEGRADATION: OCR / audio extras are optional. Missing an extra
  never crashes a plain-text conversion; it just disables that one path.

Usage
-----
    python convert.py <file-or-dir> [more ...] [options]

Common options (see --help for all):
    --out DIR         where to write .md files      (default: .markitdown/out)
    --stdout          print the full Markdown instead of a manifest
    --outline FILE    print only the heading outline of an existing .md
    --ocr auto|on|off OCR policy for images/scanned PDFs (default: auto)
    --lang LANGS      tesseract languages, e.g. "eng+rus" (default: eng+rus)
    --force           re-convert even if the cache says it's up to date
    --json            emit machine-readable JSON on stdout
    --recursive       recurse into sub-directories when given a folder
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Format tables
# --------------------------------------------------------------------------- #

# Extensions MarkItDown handles natively (text extraction, no OCR needed).
DOC_EXTS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv",
    ".html", ".htm", ".xml", ".json", ".txt", ".md", ".markdown", ".rtf",
    ".epub", ".zip", ".msg", ".rss", ".atom", ".ipynb", ".tsv",
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}

# Files we should never treat as convertible sources.
SKIP_NAMES = {".DS_Store"}
CACHE_DIRNAME = ".markitdown"


@dataclass
class Options:
    out: Path
    stdout: bool = False
    ocr: str = "auto"          # auto | on | off
    lang: str = "eng+rus"
    dpi: int = 200
    force: bool = False
    as_json: bool = False
    recursive: bool = False
    keep_data_uris: bool = False
    quiet: bool = False


@dataclass
class Result:
    src: str
    out: str | None = None
    ok: bool = False
    cached: bool = False
    ocr_used: bool = False
    chars: int = 0
    words: int = 0
    lines: int = 0
    outline: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "src": self.src,
            "out": self.out,
            "ok": self.ok,
            "cached": self.cached,
            "ocr_used": self.ocr_used,
            "chars": self.chars,
            "words": self.words,
            "lines": self.lines,
            "outline": self.outline,
            "error": self.error,
        }


# --------------------------------------------------------------------------- #
# Post-processing — the biggest single token win
# --------------------------------------------------------------------------- #

# Matches both a full data URI (`data:image/png;base64,<payload>`) and the
# already-truncated form MarkItDown emits (`data:image/png;base64...`).
_DATA_URI_RE = re.compile(r"data:[^;\s()]+;base64[,.]+[A-Za-z0-9+/=]*")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_TRAILING_WS_RE = re.compile(r"[ \t]+\n")


def postprocess(text: str, keep_data_uris: bool) -> str:
    """Strip token-heavy noise: embedded base64 blobs and runaway whitespace."""
    if not text:
        return ""
    if not keep_data_uris:
        # Embedded images/fonts as base64 can be tens of thousands of tokens
        # of pure garbage to a text agent. Replace with a tiny placeholder.
        text = _DATA_URI_RE.sub("[embedded-binary-stripped]", text)
    text = _TRAILING_WS_RE.sub("\n", text)
    text = _MULTI_BLANK_RE.sub("\n\n", text)
    return text.strip() + "\n"


def outline(text: str, limit: int = 40) -> list[str]:
    """Return the Markdown heading structure as `LINE: ### heading` strings."""
    out: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if line.startswith("#"):
            out.append(f"{i}: {line.strip()}")
            if len(out) >= limit:
                out.append("... (outline truncated)")
                break
    return out


def stats(text: str) -> tuple[int, int, int]:
    return len(text), len(text.split()), text.count("\n") + 1


# --------------------------------------------------------------------------- #
# Core conversion
# --------------------------------------------------------------------------- #

_MD_SINGLETON = None


def _markitdown():
    global _MD_SINGLETON
    if _MD_SINGLETON is None:
        from markitdown import MarkItDown  # imported lazily so --help is fast
        _MD_SINGLETON = MarkItDown(enable_plugins=False)
    return _MD_SINGLETON


def _extract_text(path: Path) -> str:
    """Run MarkItDown and return its Markdown (handles both API versions)."""
    result = _markitdown().convert(str(path))
    return getattr(result, "markdown", None) or getattr(result, "text_content", "") or ""


def _alpha_count(text: str) -> int:
    return sum(ch.isalnum() for ch in text)


def _looks_scanned(text: str, path: Path) -> bool:
    """Heuristic: very little real text for the file size ⇒ probably scanned."""
    alpha = _alpha_count(text)
    try:
        size_kb = path.stat().st_size / 1024
    except OSError:
        size_kb = 0
    # A genuine text PDF yields plenty of characters; a scan yields almost none.
    return alpha < 32 or (size_kb > 40 and alpha < size_kb)


def _extract_with_fallback(path: Path, opts: Options) -> tuple[str, bool, str | None]:
    """MarkItDown extraction with the OCR fallback. Returns (text, ocr_used, note)."""
    ext = path.suffix.lower()
    kind = (
        "image" if ext in IMAGE_EXTS
        else "audio" if ext in AUDIO_EXTS
        else "doc"
    )
    ocr_used = False
    note: str | None = None

    # 1) Native MarkItDown extraction (text PDFs, Office, HTML, EXIF, ...).
    try:
        text = _extract_text(path)
    except Exception as exc:  # noqa: BLE001 - fall back to OCR for images
        if kind != "image":
            raise
        text = f"<!-- markitdown could not parse {path.name}: {exc} -->\n"

    ocr_wanted = opts.ocr == "on" or (
        opts.ocr == "auto"
        and (
            kind == "image"
            or (ext == ".pdf" and _looks_scanned(text, path))
        )
    )

    # 2) OCR fallback for images and scanned PDFs.
    if ocr_wanted and opts.ocr != "off":
        try:
            from ocr import ocr_file, ocr_available
            if ocr_available():
                ocr_text = ocr_file(path, lang=opts.lang, dpi=opts.dpi)
                if _alpha_count(ocr_text) > _alpha_count(text):
                    # Prefer the richer of the two, keep metadata as a note.
                    header = text.strip()
                    text = (header + "\n\n" if header else "") + ocr_text
                    ocr_used = True
            elif opts.ocr == "on":
                note = ("OCR requested but tesseract is not installed "
                        "(run scripts/setup.sh)")
        except Exception as exc:  # noqa: BLE001
            if opts.ocr == "on":
                note = f"OCR failed: {exc}"

    return text, ocr_used, note


def _convert_zip(path: Path, opts: Options) -> tuple[str, bool]:
    """Convert every supported file inside a ZIP, OCR included.

    MarkItDown's own ZIP handler skips OCR for archived scans/images, so we
    extract to a temp dir and run each entry through the full pipeline.
    Nested ZIPs are handled natively (one level deep, no OCR inside them).
    Returns (markdown, any_ocr_used).
    """
    import tempfile
    import zipfile

    chunks = [f"Content from the zip file `{path.name}`:"]
    ocr_any = False
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(path) as zf:
            zf.extractall(td)  # extract() sanitizes absolute/.. member paths
        base = Path(td)
        all_files = sorted(f for f in base.rglob("*") if f.is_file())
        entries = [f for f in all_files if f.suffix.lower() in ALL_EXTS]
        skipped = [f.relative_to(base) for f in all_files
                   if f.suffix.lower() not in ALL_EXTS]

        if not entries:
            chunks.append("\n(no convertible files found in the archive)")
        for f in entries:
            rel = f.relative_to(base)
            try:
                if f.suffix.lower() == ".zip":
                    text = _extract_text(f)
                    used = False
                else:
                    text, used, _ = _extract_with_fallback(f, opts)
                ocr_any = ocr_any or used
                chunks.append(f"\n## File: {rel}\n\n{text.strip()}")
            except Exception as exc:  # noqa: BLE001 - one bad entry must not kill the archive
                chunks.append(f"\n## File: {rel}\n\n<!-- failed to convert: {exc} -->")
        if skipped:
            names = ", ".join(str(s) for s in skipped[:10])
            more = f" (+{len(skipped) - 10} more)" if len(skipped) > 10 else ""
            chunks.append(f"\n<!-- unsupported files skipped: {names}{more} -->")
    return "\n".join(chunks) + "\n", ocr_any


def convert_one(path: Path, opts: Options) -> Result:
    res = Result(src=str(path))
    try:
        if path.suffix.lower() == ".zip":
            text, res.ocr_used = _convert_zip(path, opts)
        else:
            text, res.ocr_used, res.error = _extract_with_fallback(path, opts)

        text = postprocess(text, opts.keep_data_uris)
        res.chars, res.words, res.lines = stats(text)
        res.outline = outline(text)
        res.ok = True

        # 3) Write to disk unless we are only streaming to stdout.
        if not opts.stdout:
            out_path = _out_path_for(path, opts.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(text, encoding="utf-8")
            res.out = str(out_path)
        else:
            res._full_text = text  # type: ignore[attr-defined]

    except Exception as exc:  # noqa: BLE001
        res.ok = False
        res.error = f"{type(exc).__name__}: {exc}"
    return res


def _out_path_for(src: Path, out_dir: Path) -> Path:
    """Mirror the source name into the output dir with a .md extension.

    The original suffix is folded into the name (``report_pdf.md``,
    ``report_docx.md``) so two sources that share a stem never collide.
    """
    return out_dir / (src.stem + "_" + src.suffix.lower().lstrip(".") + ".md")


# --------------------------------------------------------------------------- #
# Caching
# --------------------------------------------------------------------------- #

def _manifest_path(out_dir: Path) -> Path:
    return out_dir / "manifest.json"


def _load_manifest(out_dir: Path) -> dict:
    p = _manifest_path(out_dir)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _sig(path: Path) -> str:
    st = path.stat()
    return f"{st.st_size}:{int(st.st_mtime)}"


def _is_cached(path: Path, opts: Options, manifest: dict) -> str | None:
    """Return the cached output path if the source is unchanged, else None."""
    if opts.force or opts.stdout:
        return None
    entry = manifest.get(str(path))
    if not entry or entry.get("sig") != _sig(path):
        return None
    out = entry.get("out")
    if out and Path(out).exists():
        return out
    return None


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #

ALL_EXTS = DOC_EXTS | IMAGE_EXTS | AUDIO_EXTS
# Already Markdown — nothing to convert. Skipped when scanning a directory
# (an explicitly named .md file is still processed/normalized).
MD_EXTS = {".md", ".markdown"}


def _iter_inputs(targets: list[str], recursive: bool):
    for t in targets:
        p = Path(t)
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            for f in sorted(it):
                if (
                    f.is_file()
                    and f.suffix.lower() in ALL_EXTS
                    and f.suffix.lower() not in MD_EXTS
                    and f.name not in SKIP_NAMES
                    and CACHE_DIRNAME not in f.parts
                ):
                    yield f
        elif p.is_file():
            yield p
        else:
            yield p  # non-existent — reported as an error downstream


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #

def _print_manifest(results: list[Result], opts: Options) -> None:
    if opts.as_json:
        print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
        return

    ok = [r for r in results if r.ok]
    bad = [r for r in results if not r.ok]
    for r in results:
        if opts.stdout and r.ok and hasattr(r, "_full_text"):
            print(getattr(r, "_full_text"))
            continue
        if r.ok:
            tag = "cache" if r.cached else ("ocr" if r.ocr_used else "conv")
            print(f"[{tag}] {r.src}")
            print(f"       -> {r.out}")
            print(f"       {r.words} words, {r.lines} lines, {r.chars} chars")
            if r.outline:
                head = r.outline[:6]
                print("       outline:")
                for h in head:
                    print(f"         {h}")
                if len(r.outline) > len(head):
                    print(f"         ... (+{len(r.outline) - len(head)} more headings)")
            if r.error:
                print(f"       note: {r.error}")
        else:
            print(f"[FAIL] {r.src}: {r.error}")
    if not opts.stdout and not opts.as_json:
        print(f"\n{len(ok)} converted, {len(bad)} failed. "
              f"Read the .md files above with offset/limit to keep tokens low.")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="convert.py",
        description="Convert documents/images to Markdown (MarkItDown + OCR).",
    )
    p.add_argument("inputs", nargs="*", help="files or directories to convert")
    p.add_argument("--out", default=None, help="output dir (default: .markitdown/out)")
    p.add_argument("--stdout", action="store_true", help="print full Markdown, do not write files")
    p.add_argument("--outline", metavar="MD", help="print the heading outline of an existing .md and exit")
    p.add_argument("--ocr", choices=["auto", "on", "off"], default="auto", help="OCR policy (default: auto)")
    p.add_argument("--lang", default="eng+rus", help="tesseract languages (default: eng+rus)")
    p.add_argument("--dpi", type=int, default=200, help="render DPI for PDF OCR (default: 200)")
    p.add_argument("--force", action="store_true", help="ignore cache and re-convert")
    p.add_argument("--json", dest="as_json", action="store_true", help="machine-readable JSON output")
    p.add_argument("--recursive", action="store_true", help="recurse into sub-directories")
    p.add_argument("--keep-data-uris", action="store_true", help="do not strip embedded base64 blobs")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # --outline is a standalone helper: cheap heading map of an existing file.
    if args.outline:
        text = Path(args.outline).read_text(encoding="utf-8", errors="replace")
        heads = outline(text, limit=200)
        print("\n".join(heads) if heads else "(no Markdown headings found)")
        return 0

    if not args.inputs:
        build_parser().print_help()
        return 2

    out_dir = Path(args.out) if args.out else Path(CACHE_DIRNAME) / "out"
    opts = Options(
        out=out_dir,
        stdout=args.stdout,
        ocr=args.ocr,
        lang=args.lang,
        dpi=args.dpi,
        force=args.force,
        as_json=args.as_json,
        recursive=args.recursive,
        keep_data_uris=args.keep_data_uris,
    )

    # Make `import ocr` work regardless of the caller's CWD.
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    manifest = {} if opts.stdout else _load_manifest(out_dir)
    results: list[Result] = []

    for src in _iter_inputs(args.inputs, opts.recursive):
        if not src.exists():
            results.append(Result(src=str(src), ok=False, error="file not found"))
            continue

        cached_out = _is_cached(src, opts, manifest)
        if cached_out:
            text = Path(cached_out).read_text(encoding="utf-8", errors="replace")
            c, w, ln = stats(text)
            results.append(Result(
                src=str(src), out=cached_out, ok=True, cached=True,
                chars=c, words=w, lines=ln, outline=outline(text),
            ))
            continue

        res = convert_one(src, opts)
        results.append(res)
        if res.ok and res.out and not opts.stdout:
            manifest[str(src)] = {"sig": _sig(src), "out": res.out, "ts": int(time.time())}

    if not opts.stdout:
        out_dir.mkdir(parents=True, exist_ok=True)
        _manifest_path(out_dir).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    _print_manifest(results, opts)
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
