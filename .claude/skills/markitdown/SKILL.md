---
name: markitdown
description: >-
  Convert documents and images to clean Markdown for the agent to read, using
  Microsoft MarkItDown plus a Tesseract OCR fallback. Use this whenever the
  user uploads, points at, or asks about a non-Markdown file — PDF, Word
  (docx), PowerPoint (pptx), Excel (xlsx), CSV/TSV, HTML, XML, JSON, EPUB,
  ZIP, Outlook .msg, or an image (PNG/JPG/TIFF) — or asks to "convert to
  markdown", "extract text", "read this PDF", "OCR this scan/screenshot",
  "summarize this document", or to look at diagrams/stamps/handwriting inside
  a document. Handles scanned/image-only PDFs and photos of text via OCR, can
  render PDF pages to PNG for visual inspection, and keeps token use low by
  writing Markdown to files and reporting only a short outline instead of
  dumping full contents.
---

# MarkItDown Skill

Turn almost any file into Markdown the agent can actually read — **without
burning tokens**. MarkItDown extracts embedded text (real PDFs, Office files,
HTML, CSV…); a Tesseract OCR fallback recovers text from **scanned PDFs and
images**. Output is written to disk and summarized, so you pull only the parts
you need into context.

## When to use this skill

Trigger on any of these:

- A file that is **not** already plain text/Markdown is uploaded or referenced
  (`.pdf .docx .pptx .xlsx .csv .tsv .html .xml .json .epub .zip .msg`,
  images `.png .jpg .jpeg .tif .tiff .bmp .webp`, audio `.wav .mp3 .m4a`).
- The user says: *convert to markdown*, *extract the text*, *read this PDF*,
  *what does this document say*, *OCR this scan/screenshot/photo*,
  *summarize this file*, *pull the tables out of this spreadsheet*.
- You need the contents of a binary document to answer a question.

If the file is **already** `.md`/`.txt`/source code, just read it directly —
you do not need this skill.

## First run: make sure the tools are installed

The scripts need the `markitdown` Python package (and, for OCR, the
`tesseract` binary + `pytesseract`). Bootstrap once — it is idempotent and
no-ops when everything is present:

```bash
bash .claude/skills/markitdown/scripts/setup.sh          # + OCR (eng, rus)
bash .claude/skills/markitdown/scripts/setup.sh --no-ocr # text formats only
bash .claude/skills/markitdown/scripts/setup.sh --langs "eng rus deu"
```

If `tesseract` can't be installed (no root/network), text formats still work;
only OCR of scans/images is disabled.

## The core workflow (low token cost — do this by default)

**Convert to a file, then read only what you need.** Do **not** pipe whole
documents into context.

1. **Convert.** Point `convert.py` at a file or a folder. It writes `.md`
   files under `.markitdown/out/` and prints a compact manifest — path, word
   count, and a heading outline — *not* the contents.

   ```bash
   python3 .claude/skills/markitdown/scripts/convert.py path/to/file.pdf
   python3 .claude/skills/markitdown/scripts/convert.py ./inbox --recursive
   ```

2. **Skim the outline** in that manifest to find the relevant section.

3. **Read selectively** with the normal Read tool using `offset`/`limit`,
   jumping to the line numbers from the outline — instead of reading the whole
   `.md`. For a big file, get a fuller map first:

   ```bash
   python3 .claude/skills/markitdown/scripts/convert.py --outline .markitdown/out/file_pdf.md
   ```

Only fall back to dumping full text (`--stdout`) for genuinely small files or
when the user explicitly wants everything inline. See
`references/token-optimization.md` for the full rationale and numbers.

## OCR: scanned PDFs and images

OCR is automatic. With `--ocr auto` (the default), the converter runs OCR when
a file is an image, or when a PDF yields almost no embedded text (i.e. it is a
scan). You usually don't need to think about it.

```bash
# Force OCR on (e.g. a PDF with a thin/garbled text layer):
python3 .claude/skills/markitdown/scripts/convert.py scan.pdf --ocr on

# Pick languages (must be installed via setup.sh --langs):
python3 .claude/skills/markitdown/scripts/convert.py photo.jpg --lang rus
python3 .claude/skills/markitdown/scripts/convert.py doc.pdf   --lang "eng+rus"

# Higher fidelity for small/blurry scans (slower):
python3 .claude/skills/markitdown/scripts/convert.py faint.pdf --ocr on --dpi 300

# Disable OCR entirely (text layers only):
python3 .claude/skills/markitdown/scripts/convert.py file.pdf --ocr off
```

Quick OCR of a single image straight to stdout: `python3
.claude/skills/markitdown/scripts/ocr.py image.png --lang eng+rus`.

## Looking at images visually (diagrams, stamps, handwriting, photos)

OCR recovers **printed text only**. When a document contains anything that
must be *seen* — charts, diagrams, tables drawn as pictures, stamps, seals,
signatures, handwriting, photos, or a layout you need to verify — look at the
actual image:

- **Standalone image files** (`.png .jpg .jpeg .tif ...`): open the original
  file directly with the **Read tool** — it renders images visually. Do this
  *in addition to* reading the OCR `.md` when the picture matters.
- **PDF pages**: render the page(s) you need to PNG first, then Read the PNG:

  ```bash
  python3 .claude/skills/markitdown/scripts/pages.py doc.pdf --pages 3
  python3 .claude/skills/markitdown/scripts/pages.py doc.pdf --pages 2-5,8 --dpi 200
  ```

  It prints one PNG path per line (default output: `.markitdown/pages/`).

Rule of thumb: use the `.md` to *search and quote* text cheaply; view the
image/page when the question involves anything visual, or when OCR output
looks garbled or suspiciously empty for a page. Render only the specific
pages you need — each viewed image costs tokens, so don't render `--pages all`
of a long document unless the user asks for a full visual review.

## Automatic conversion when files are uploaded

Enable hooks so **every uploaded/dropped file is converted to Markdown
automatically** — you never have to run the converter by hand:

```bash
python3 .claude/skills/markitdown/scripts/install_hooks.py          # enable
python3 .claude/skills/markitdown/scripts/install_hooks.py --uninstall
```

This adds two hooks to `.claude/settings.json` (existing settings are
preserved):

- **SessionStart** — installs deps if needed, then converts anything already
  present.
- **UserPromptSubmit** — converts files added mid-session.

On each run the hook converts **only new/changed** files (it caches by
size+mtime) and prints a one-line-per-file note pointing at the generated
`.md` — never the contents — so the per-prompt cost is tiny, and it prints
**nothing at all** when nothing changed. It scans the project root plus
`inbox/ uploads/ attachments/ docs/ data/ downloads/` if they exist; override
with `MARKITDOWN_WATCH_DIRS=/abs/dir1:/abs/dir2`.

When you see a `MarkItDown auto-converted…` note, treat the listed `.md` files
as the source of truth and read those (with `offset`/`limit`) instead of the
originals.

### CI conversion and large files (repo `inbox/` + links)

If the project has `.github/workflows/markitdown.yml`, files pushed into
`inbox/` are converted by GitHub Actions into `converted/*.md` — even with no
session running. Files too big for GitHub (>25 MB web / >100 MB push) go in as
URLs: one link per line in `inbox/links.txt` (direct, Google Drive, Yandex
Disk, Mail.ru Cloud, Dropbox). CI downloads them with `scripts/fetch.py`, converts, and
commits only the Markdown; processed links are tracked in
`converted/.links_done.json` and never re-downloaded. You can also run it
manually:

```bash
python3 .claude/skills/markitdown/scripts/fetch.py inbox/links.txt --out /tmp/fetched
python3 .claude/skills/markitdown/scripts/fetch.py --url https://... --out /tmp/fetched
```

## Command reference (`convert.py`)

| Flag | Meaning |
| --- | --- |
| *(positional)* | one or more files/dirs to convert |
| `--out DIR` | output directory (default `.markitdown/out`) |
| `--recursive` | recurse into sub-directories of a folder |
| `--stdout` | print full Markdown instead of writing files (use sparingly) |
| `--outline MD` | print only the heading outline of an existing `.md`, then exit |
| `--ocr auto\|on\|off` | OCR policy (default `auto`) |
| `--lang LANGS` | Tesseract languages, e.g. `eng+rus` (default `eng+rus`) |
| `--dpi N` | render DPI for PDF OCR (default `200`; raise to `300` for faint scans) |
| `--force` | ignore the cache and re-convert |
| `--json` | machine-readable JSON manifest on stdout |
| `--keep-data-uris` | keep embedded base64 blobs (off by default; they waste tokens) |

Exit code is `0` when every input converted, `1` if any failed.

## How it keeps token use low (summary)

- Writes Markdown to files; reports only path + word count + heading outline.
- Strips embedded base64 image/font blobs (`data:…;base64,…`) — often the
  single biggest source of junk tokens.
- Collapses runaway blank lines and trailing whitespace.
- Caches by size+mtime, so re-runs and the auto-hook never re-convert
  unchanged files.
- The auto-hook is silent when there's nothing new.

## Troubleshooting

- **`ModuleNotFoundError: markitdown`** → run `setup.sh`.
- **PDF returns empty / OCR not firing** → it may be a scan with no text layer;
  force it with `--ocr on`, and ensure `tesseract` is installed
  (`setup.sh`). For faint scans add `--dpi 300`.
- **Wrong-language OCR (garbled Cyrillic/accents)** → pass the right `--lang`
  and install that language pack (`setup.sh --langs "eng rus"`).
- **`_cffi_backend` / cryptography panic on import** → `setup.sh` upgrades
  `cffi` first; if you hit it manually, `pip install --upgrade cffi`.
- More detail and the full format matrix: `references/troubleshooting.md`,
  `references/formats.md`.
