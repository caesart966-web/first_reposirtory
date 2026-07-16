#!/usr/bin/env python3
"""
hook.py — automatic conversion on file upload / session start.

Wire this into Claude Code as a `SessionStart` and/or `UserPromptSubmit`
hook (see scripts/install_hooks.py). On every run it:

  1. Scans the watch directories for supported documents/images.
  2. Converts only the ones that are new or changed since last time
     (cheap: it compares size+mtime against .markitdown/out/manifest.json
     before importing anything heavy).
  3. Prints a SHORT note naming the generated .md files — never their
     contents — so the agent spends tokens on the Markdown it actually
     needs, on demand, via Read with offset/limit.

If nothing changed it prints nothing and exits 0, so it is safe to run on
every prompt. It never raises into the host: any failure degrades to a
one-line hint (or silence) and exit 0.

Watch directories (first match wins):
  * $MARKITDOWN_WATCH_DIRS  — colon-separated absolute/relative dirs
  * else: repo root (non-recursive) + ./inbox ./uploads ./attachments
          ./docs ./data (recursive), whichever exist.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Reuse the converter's engine so behaviour stays identical to the CLI.
import convert as C  # noqa: E402

RECURSIVE_DIRS = ["inbox", "uploads", "attachments", "docs", "data", "downloads"]
MAX_FILES_PER_RUN = int(os.environ.get("MARKITDOWN_MAX_FILES", "25"))


def _read_hook_stdin() -> dict:
    """Claude Code passes a JSON payload on stdin; tolerate its absence."""
    if sys.stdin is None or sys.stdin.closed:
        return {}
    try:
        raw = sys.stdin.read()
    except Exception:  # noqa: BLE001
        return {}
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _project_root(payload: dict) -> Path:
    for key in ("cwd", "project_dir", "projectDir", "workspace"):
        v = payload.get(key)
        if v and Path(v).is_dir():
            return Path(v)
    return Path.cwd()


def _watch_dirs(root: Path) -> list[tuple[Path, bool]]:
    """Return (dir, recursive) pairs to scan."""
    env = os.environ.get("MARKITDOWN_WATCH_DIRS")
    if env:
        return [(Path(p), True) for p in env.split(os.pathsep) if Path(p).is_dir()]
    dirs: list[tuple[Path, bool]] = [(root, False)]  # root itself, shallow
    for name in RECURSIVE_DIRS:
        d = root / name
        if d.is_dir():
            dirs.append((d, True))
    return dirs


def _candidates(dirs: list[tuple[Path, bool]]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for d, recursive in dirs:
        it = d.rglob("*") if recursive else d.glob("*")
        for f in it:
            if (
                f.is_file()
                and f.suffix.lower() in C.ALL_EXTS
                and f.suffix.lower() not in C.MD_EXTS
                and f.name not in C.SKIP_NAMES
                and C.CACHE_DIRNAME not in f.parts
                and f.resolve() not in seen
            ):
                seen.add(f.resolve())
                out.append(f)
    return out


def main() -> int:
    payload = _read_hook_stdin()
    root = _project_root(payload)
    out_dir = root / C.CACHE_DIRNAME / "out"

    try:
        manifest = C._load_manifest(out_dir)
        opts = C.Options(out=out_dir)  # defaults: OCR auto, strip data URIs, cache on

        pending: list[Path] = []
        for src in _candidates(_watch_dirs(root)):
            if C._is_cached(src, opts, manifest) is None:
                pending.append(src)

        if not pending:
            return 0  # nothing new — stay silent, spend no tokens

        pending = pending[:MAX_FILES_PER_RUN]
        results = []
        for src in pending:
            res = C.convert_one(src, opts)
            results.append(res)
            if res.ok and res.out:
                manifest[str(src)] = {"sig": C._sig(src), "out": res.out}

        out_dir.mkdir(parents=True, exist_ok=True)
        C._manifest_path(out_dir).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        ok = [r for r in results if r.ok]
        if ok:
            lines = ["MarkItDown auto-converted new file(s) to Markdown "
                     "(read these instead of the originals):"]
            for r in ok:
                rel = os.path.relpath(r.out, root)
                extra = ", OCR" if r.ocr_used else ""
                lines.append(f"  - {os.path.relpath(r.src, root)} -> {rel} "
                             f"({r.words} words{extra})")
            lines.append("Use Read with offset/limit on the .md files to keep token use low.")
            if any(r.ocr_used for r in ok):
                lines.append("Some files were OCRed (text only): if diagrams, stamps, "
                             "handwriting or layout matter, view the original image with "
                             "Read, or render PDF pages via scripts/pages.py.")
            print("\n".join(lines))
        return 0
    except Exception as exc:  # noqa: BLE001 - never break the host session
        # A hook must not crash the prompt; a quiet hint is enough.
        sys.stderr.write(f"markitdown hook skipped: {exc}\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
