# Token optimization

The whole point of this skill is to let the agent use big documents **without**
paying to keep them in context. Here is why each mechanism matters and how to
get the most out of it.

## The core idea: files, not context

A 40-page PDF can be 30–60k tokens of Markdown. Reading all of it to answer one
question is wasteful and can blow the context window. Instead:

1. **Convert to a file.** `convert.py` writes `.md` under `.markitdown/out/`
   and prints only a *manifest*: path, word/line/char counts, and the heading
   outline. That manifest is a few hundred tokens regardless of document size.
2. **Locate.** Read the outline; each heading is tagged with its line number.
3. **Read the slice.** Use the Read tool with `offset`/`limit` around the
   relevant heading. You pull in a few hundred lines, not tens of thousands.

For a fuller heading map of an already-converted file:

```bash
python3 scripts/convert.py --outline .markitdown/out/report_pdf.md
```

Only use `--stdout` (full dump) for genuinely small files, or when the user
explicitly asks to see the whole thing inline.

## Post-processing that shrinks output

Applied automatically to every conversion:

- **Strip base64 data-URIs.** `data:image/png;base64,…` blobs embedded in
  HTML/PDF/Office files can be tens of thousands of tokens of pure noise to a
  text agent. They are replaced with `[embedded-binary-stripped]`. Disable with
  `--keep-data-uris` only if you specifically need the raw bytes.
- **Collapse whitespace.** Runs of 3+ blank lines become one blank line;
  trailing spaces are removed.

## Caching: never pay twice

Each output dir has a `manifest.json` keyed by source path, storing the
source's `size:mtime`. On the next run (manual or via the auto-hook), an
unchanged file is reported from cache and **not** re-converted. This makes:

- re-running `convert.py` on a folder cheap, and
- the `UserPromptSubmit` auto-hook safe to fire on every prompt.

Use `--force` to bypass the cache after changing OCR settings.

## OCR cost notes

- OCR (`--ocr on/auto`) is CPU work, not tokens — but higher `--dpi` is slower.
  Start at the default `200`; only raise to `300` when text is small/faint.
- OCR output is plain text (no images), so it is already token-lean.

## Rules of thumb for the agent

- Default to the manifest + selective Read. Reach for `--stdout` rarely.
- When the auto-hook prints "auto-converted…", read the listed `.md`, not the
  binary original.
- For "find X in this document" tasks, prefer `grep` over the generated `.md`
  to locate lines, then Read just those — cheaper than reading to search.
- Convert a whole folder once (`--recursive`) rather than one file per prompt;
  the cache makes the repeat scans free.
