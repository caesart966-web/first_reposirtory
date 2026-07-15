#!/usr/bin/env bash
# setup.sh — idempotent dependency bootstrap for the MarkItDown Skill.
#
# Installs (only what is missing):
#   * markitdown[all]  — the converter + all format extras (PDF, docx, ...).
#   * pytesseract      — Python binding for OCR.
#   * tesseract-ocr    — the OCR engine + eng/rus language data (best-effort).
#
# Safe to run repeatedly and safe to run from a SessionStart hook: it no-ops
# fast when everything is already present and never exits non-zero in a way
# that would abort a session (the final line always succeeds).
#
# Usage:  bash scripts/setup.sh [--no-ocr] [--langs "eng rus deu"]
set -u

WITH_OCR=1
LANGS="eng rus"
while [ $# -gt 0 ]; do
  case "$1" in
    --no-ocr) WITH_OCR=0 ;;
    --langs)  LANGS="${2:-eng}"; shift ;;
    *) echo "unknown arg: $1" >&2 ;;
  esac
  shift
done

log() { printf '  %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

PYBIN="$(command -v python3 || command -v python)"
if [ -z "$PYBIN" ]; then
  echo "python3 not found — cannot continue" >&2
  exit 0
fi

echo "MarkItDown Skill setup"

# --- 1. Python packages ----------------------------------------------------- #
need_pip=0
"$PYBIN" -c "import markitdown" 2>/dev/null || need_pip=1
if [ "$WITH_OCR" = "1" ]; then
  "$PYBIN" -c "import pytesseract" 2>/dev/null || need_pip=1
fi

if [ "$need_pip" = "1" ]; then
  log "installing Python packages (markitdown[all], pytesseract)..."
  PKGS="markitdown[all]"
  [ "$WITH_OCR" = "1" ] && PKGS="$PKGS pytesseract"
  # cffi is pinned first: some base images ship a broken cryptography/_cffi_backend.
  "$PYBIN" -m pip install --quiet --upgrade cffi >/dev/null 2>&1 || true
  if ! "$PYBIN" -m pip install --quiet $PKGS; then
    log "pip install reported an error; retrying core package only"
    "$PYBIN" -m pip install --quiet "markitdown[pdf]" || \
      log "WARNING: could not install markitdown — conversions will be unavailable"
  fi
else
  log "Python packages already present."
fi

# --- 2. Tesseract engine (optional) ----------------------------------------- #
if [ "$WITH_OCR" = "1" ]; then
  if have tesseract; then
    log "tesseract already installed ($(tesseract --version 2>&1 | head -1))."
  else
    log "installing tesseract-ocr engine..."
    lang_pkgs=""
    for l in $LANGS; do lang_pkgs="$lang_pkgs tesseract-ocr-$l"; done
    if have apt-get; then
      (apt-get update -qq && apt-get install -y -qq tesseract-ocr $lang_pkgs) >/dev/null 2>&1 \
        || log "WARNING: apt install failed (no root/network?). OCR will be disabled."
    elif have brew; then
      brew install tesseract >/dev/null 2>&1 || log "WARNING: brew install tesseract failed."
    elif have apk; then
      apk add --no-cache tesseract-ocr >/dev/null 2>&1 || log "WARNING: apk add failed."
    else
      log "no supported package manager found; skipping tesseract."
      log "install it manually to enable OCR (https://github.com/tesseract-ocr/tesseract)."
    fi
  fi
fi

# --- 3. Report -------------------------------------------------------------- #
echo "Status:"
"$PYBIN" - <<'PY'
def check(mod):
    try:
        __import__(mod); return "ok"
    except Exception as e:
        return f"MISSING ({e.__class__.__name__})"
import shutil
print(f"  markitdown : {check('markitdown')}")
print(f"  pytesseract: {check('pytesseract')}")
print(f"  tesseract  : {'ok' if shutil.which('tesseract') else 'MISSING (OCR disabled)'}")
PY

echo "Setup complete."
exit 0
