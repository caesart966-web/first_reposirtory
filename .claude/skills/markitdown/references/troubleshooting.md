# Troubleshooting

## Installation

**`ModuleNotFoundError: No module named 'markitdown'`**
Run `bash scripts/setup.sh`. If pip has no network, install offline from a
wheel cache, or copy an environment that already has `markitdown`.

**`pyo3_runtime.PanicException` / `No module named '_cffi_backend'` on import**
A broken `cryptography`/`cffi` in the base image. Fix:
```bash
pip install --upgrade cffi
```
`setup.sh` does this automatically before installing markitdown.

**`ERROR: Cannot uninstall cryptography … RECORD file not found`**
The distro-managed `cryptography` can't be removed by pip. It's harmless here —
upgrading `cffi` alone resolves the import panic; you don't need to upgrade
`cryptography`.

## OCR

**A PDF converts to an empty or near-empty `.md`**
It's probably a scan with no text layer. Confirm and force OCR:
```bash
python3 scripts/convert.py file.pdf --ocr on
```
Ensure the engine is present: `tesseract --version`. If missing, `bash
scripts/setup.sh` (needs root/apt, or install tesseract manually).

**OCR text is garbled / wrong language**
Pass the correct language and make sure its data is installed:
```bash
bash scripts/setup.sh --langs "eng rus"
python3 scripts/convert.py doc.pdf --ocr on --lang "eng+rus"
```
List installed languages: `tesseract --list-langs`.

**OCR quality is poor on small or faint scans**
Increase render resolution:
```bash
python3 scripts/convert.py faint.pdf --ocr on --dpi 300
```
Higher DPI is slower but sharper. `400` is the practical ceiling.

**`OCR requested but tesseract is not installed`**
The binary isn't on PATH. Install it (`setup.sh`, or your OS package manager:
`apt-get install tesseract-ocr`, `brew install tesseract`, `apk add
tesseract-ocr`).

## Auto-conversion hook

**Files aren't auto-converting**
1. Confirm hooks are installed: check `.claude/settings.json` has
   `SessionStart` / `UserPromptSubmit` entries calling `hook.py`
   (`python3 scripts/install_hooks.py` to add them).
2. `SessionStart` only fires on a **new** session — restart to pick it up.
3. The file must be under a watched dir: project root (shallow) or
   `inbox/ uploads/ attachments/ docs/ data/ downloads/`. Override with
   `MARKITDOWN_WATCH_DIRS=/abs/dir1:/abs/dir2`.
4. The extension must be supported (see `formats.md`).

**The hook is noisy**
It prints only when it converts something new. To reduce scope, set
`MARKITDOWN_WATCH_DIRS` to a single upload folder, or install with
`--no-prompt-hook` to keep only the SessionStart scan.

**Run the hook manually to debug**
```bash
echo '{"cwd":"'"$PWD"'"}' | python3 scripts/hook.py
```

## Output & caching

**Stale output after changing OCR settings**
The cache keys on source size+mtime, not on flags. Force a rebuild:
```bash
python3 scripts/convert.py file.pdf --force --ocr on --dpi 300
```

**Where do outputs go?**
`.markitdown/out/<name>_<ext>.md` (e.g. `report_pdf.md`) plus a
`manifest.json`. The `.markitdown/` dir is safe to delete; it just rebuilds.
Add it to `.gitignore` (this repo already does).

**A specific file fails but others succeed**
Run just that file with `--json` to see the exact error:
```bash
python3 scripts/convert.py problem.docx --json
```
Encrypted/corrupt files are the usual cause — supply a clean, decrypted copy.
