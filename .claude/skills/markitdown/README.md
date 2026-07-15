# MarkItDown Skill

A Claude Code / Agent **Skill** that converts almost any file into clean
Markdown the agent can read — with an OCR fallback for scanned PDFs and
images, optional automatic conversion when files are uploaded, and a workflow
built to keep token use low.

> The instructions the agent follows live in [`SKILL.md`](./SKILL.md). This
> README is for humans setting it up.

## What it does

- **Converts** PDF, Word, PowerPoint, Excel, CSV/TSV, HTML, XML, JSON, EPUB,
  ZIP, Outlook `.msg`, images, and more to Markdown (via Microsoft MarkItDown).
- **OCR** for scanned/image-only PDFs and photos of text (via Tesseract) —
  automatic when a PDF has no text layer.
- **Auto-conversion on upload** through optional SessionStart / UserPromptSubmit
  hooks — dropped files become Markdown with no manual step.
- **Low token cost** by design: writes Markdown to files and reports only an
  outline, strips embedded base64 blobs, and caches so nothing is converted
  twice.

## Install

```bash
# 1. Dependencies (markitdown + tesseract OCR for English & Russian).
bash .claude/skills/markitdown/scripts/setup.sh

# 2. (Optional) Enable automatic conversion of uploaded files.
python3 .claude/skills/markitdown/scripts/install_hooks.py
```

`setup.sh` is idempotent (safe to re-run) and degrades gracefully if OCR can't
be installed. Use `--no-ocr` for text formats only, or `--langs "eng rus deu"`
to add languages.

## Use

```bash
S=.claude/skills/markitdown/scripts

# Convert one file (writes .markitdown/out/<name>_<ext>.md, prints an outline).
python3 $S/convert.py report.pdf

# Convert a whole folder, recursively.
python3 $S/convert.py ./inbox --recursive

# Force OCR (e.g. a scan with a garbled text layer), pick a language.
python3 $S/convert.py scan.pdf --ocr on --lang "eng+rus" --dpi 300

# Just the heading outline of an already-converted file.
python3 $S/convert.py --outline .markitdown/out/report_pdf.md

# OCR a single image straight to stdout.
python3 $S/ocr.py photo.jpg --lang rus
```

Then read the generated `.md` with the Read tool using `offset`/`limit` around
the outline's line numbers — don't dump the whole file.

## Layout

```
.claude/skills/markitdown/
├── SKILL.md                 # instructions the agent reads
├── README.md                # this file
├── requirements.txt
├── scripts/
│   ├── convert.py           # core CLI: convert files/dirs → Markdown
│   ├── ocr.py               # Tesseract OCR helpers (images, scanned PDFs)
│   ├── hook.py              # auto-convert on session start / prompt submit
│   ├── install_hooks.py     # wire/unwire the auto-conversion hooks
│   └── setup.sh             # idempotent dependency bootstrap
└── references/
    ├── formats.md           # full format support matrix
    ├── token-optimization.md# how/why token use stays low
    └── troubleshooting.md   # common problems and fixes
```

Output goes to `.markitdown/out/` (git-ignored; safe to delete — it rebuilds).

## Credits

Built on [Microsoft MarkItDown](https://github.com/microsoft/markitdown) and
[Tesseract OCR](https://github.com/tesseract-ocr/tesseract).
