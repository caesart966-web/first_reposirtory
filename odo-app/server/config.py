"""Пути и настройки. Всё, что можно, берётся из переменных окружения."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent            # odo-app/
REPO = ROOT.parent                                        # корень репозитория
ENGINE_DIR = Path(os.environ.get("ODO_ENGINE_DIR", REPO / ".claude" / "skills" / "sro-odo")).resolve()
SCRIPTS_DIR = ENGINE_DIR / "scripts"
DATA_DIR = Path(os.environ.get("ODO_DATA_DIR", ROOT / "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "odo.sqlite3"
REPORTS_DIR = Path(os.environ.get("ODO_REPORTS_DIR", DATA_DIR / "отчёты")).resolve()   # готовые заключения, ответы, реестры

APP_PASSWORD = os.environ.get("ODO_PASSWORD") or None       # пусто — без пароля
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or None
LLM_MODEL = os.environ.get("ODO_LLM_MODEL", "claude-sonnet-5")
HOST = os.environ.get("ODO_HOST", "127.0.0.1")
PORT = int(os.environ.get("ODO_PORT", "8765"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
