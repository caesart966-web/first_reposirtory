# Supported formats

MarkItDown (Microsoft) does the extraction; this skill adds an OCR fallback
and token-shrinking post-processing on top. Extraction quality below is a
rough guide.

## Documents (native text extraction — no OCR needed)

| Format | Extensions | Notes |
| --- | --- | --- |
| PDF (text layer) | `.pdf` | Extracted via pdfminer. Scanned PDFs → OCR fallback (see below). |
| Word | `.docx` (`.doc` best-effort) | Headings, lists, tables preserved. |
| PowerPoint | `.pptx` (`.ppt` best-effort) | One section per slide; speaker notes included. |
| Excel | `.xlsx`, `.xls` | Each sheet becomes a Markdown table. |
| CSV / TSV | `.csv`, `.tsv` | Rendered as a Markdown table. |
| HTML | `.html`, `.htm` | Converted with markdownify; data-URIs stripped. |
| XML / RSS / Atom | `.xml`, `.rss`, `.atom` | Structured text. |
| JSON | `.json` | Pretty-printed / flattened. |
| EPUB | `.epub` | Chapters concatenated. |
| Jupyter | `.ipynb` | Markdown + code cells. |
| Outlook message | `.msg` | Headers + body. |
| ZIP archive | `.zip` | Each contained file runs through the full pipeline — including OCR for archived scans/images — and results are concatenated into one `.md` with a `## File:` section per entry. Unsupported entries are listed as skipped. Nested ZIPs: one level deep, no OCR inside. |
| Plain text / Markdown | `.txt`, `.md`, `.markdown`, `.rtf` | Passed through / normalized. |

## Images (OCR path)

| Extensions | Behaviour |
| --- | --- |
| `.png .jpg .jpeg .tif .tiff .bmp .gif .webp` | MarkItDown reads EXIF metadata; this skill adds Tesseract OCR to recover any text in the pixels. Requires `tesseract` (`setup.sh`). |

## Scanned / image-only PDFs

A PDF with no real text layer (a scan or export of images) returns almost
nothing from pdfminer. With `--ocr auto` (default) the converter detects this
(very low character count for the file size) and OCRs each page: `pypdfium2`
renders the page to a bitmap, Tesseract reads it. Page breaks are marked with
`<!-- page N -->`.

Force it explicitly with `--ocr on` if a thin/garbled text layer fools the
heuristic. Raise `--dpi 300` for small or faint scans.

## Audio (optional, transcription)

| Extensions | Behaviour |
| --- | --- |
| `.wav .mp3 .m4a .flac .ogg` | Transcription via MarkItDown's audio support when the `[audio-transcription]` extra is installed (`pip install 'markitdown[all]'`). Speech recognition may require network/model download. |

## What is *not* handled well

- Encrypted / password-protected files (supply a decrypted copy).
- Handwriting (Tesseract is tuned for printed text).
- Complex multi-column magazine layouts may reflow imperfectly.
- Charts/diagrams as images yield only any embedded text via OCR, not a
  description — but the agent can *look* at them: Read image files directly
  (the Read tool renders them), and render PDF pages to PNG with
  `scripts/pages.py` for visual inspection.
- Handwriting: OCR won't read it, but viewing the image/page (above) lets the
  agent read it visually in many cases.
