"""Конфигурация backend'а. Всё через переменные окружения, с разумными дефолтами.

Ключевые переменные:
  CONSTRUCTION_MCP_DB        путь к файлу SQLite (по умолчанию data/construction.db)
  CONSTRUCTION_SKILL_DIR     путь к .claude/skills/construction-control (автопоиск)
  CONSTRUCTION_MCP_STORAGE   каталог для видео/кадров (по умолчанию data/storage)
  ANTHROPIC_API_KEY          ключ для мультимодального анализа кадров (иначе офлайн-заглушка)
  CONSTRUCTION_MCP_VISION_MODEL  id модели для анализа кадров (по умолчанию claude-sonnet-5)
  CONSTRUCTION_MCP_OFFLINE   принудительный офлайн-режим (1/true)
"""
from __future__ import annotations

import os
from pathlib import Path


def _find_skill_dir() -> Path | None:
    env = os.environ.get("CONSTRUCTION_SKILL_DIR")
    if env and Path(env).exists():
        return Path(env)
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        cand = parent / ".claude" / "skills" / "construction-control"
        if (cand / "schemas").is_dir():
            return cand
    return None


SKILL_DIR: Path | None = _find_skill_dir()
SCHEMAS_DIR: Path | None = (SKILL_DIR / "schemas") if SKILL_DIR else None

_DATA_DIR = Path(os.environ.get("CONSTRUCTION_MCP_DATA", Path.cwd() / "data"))
DB_PATH = Path(os.environ.get("CONSTRUCTION_MCP_DB", _DATA_DIR / "construction.db"))
STORAGE_DIR = Path(os.environ.get("CONSTRUCTION_MCP_STORAGE", _DATA_DIR / "storage"))

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
VISION_MODEL = os.environ.get("CONSTRUCTION_MCP_VISION_MODEL", "claude-sonnet-5")

_forced_offline = os.environ.get("CONSTRUCTION_MCP_OFFLINE", "").lower() in ("1", "true", "yes")
OFFLINE = _forced_offline or not ANTHROPIC_API_KEY

# Пороги расчётов (дублируют references/deviation-logic.md, конфигурируемы).
ON_TRACK_TOLERANCE_PP = float(os.environ.get("CONSTRUCTION_MCP_TOLERANCE_PP", "5"))
OVERDUE_DAYS_HIGH = int(os.environ.get("CONSTRUCTION_MCP_OVERDUE_DAYS_HIGH", "7"))
LOW_CONFIDENCE = float(os.environ.get("CONSTRUCTION_MCP_LOW_CONFIDENCE", "0.5"))
AUTO_ACCEPT_CONFIDENCE = float(os.environ.get("CONSTRUCTION_MCP_AUTO_ACCEPT", "0.8"))


def ensure_dirs() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
