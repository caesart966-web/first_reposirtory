"""Цвета и разбор строк журнала.

Отделено от ui_theme.py намеренно: здесь нет tkinter, поэтому раскраску
журнала можно проверять тестами на любой машине, в том числе там, где
графической подсистемы нет вовсе.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Палитра
# ---------------------------------------------------------------------------

BG = "#EEF1F6"          # фон окна
CARD = "#FFFFFF"        # фон карточек
BORDER = "#D9E0EA"
TEXT = "#1B2733"
MUTED = "#6B7A8C"

ACCENT = "#2563EB"
ACCENT_HOVER = "#1D4ED8"
ACCENT_DIM = "#A9C0F5"

OK, OK_BG = "#15803D", "#DCFCE7"
BAD, BAD_BG = "#B91C1C", "#FEE2E2"
WARN, WARN_BG = "#B45309", "#FEF3C7"

LOG_BG = "#FBFCFE"
TROUGH = "#E1E7F0"

LOG_TAGS = {
    "ok": {"foreground": OK},
    "bad": {"foreground": BAD},
    "warn": {"foreground": WARN},
    "muted": {"foreground": MUTED},
    "head": {"foreground": TEXT},
    "alert": {"foreground": BAD},
    "body": {"foreground": TEXT},
}


def classify(line: str) -> str:
    """К какому виду отнести строку журнала — от этого зависит её цвет.

    Порядок проверок важен: «→ не удалось проверить» должно разбираться
    раньше «→ нет», иначе жёлтые строки покраснеют.
    """
    stripped = line.strip()
    if not stripped:
        return "muted"

    low = stripped.lower()

    if low.startswith(("ошибка", "сбой")):
        return "alert"
    # Именно начало строки: иначе компания с «Вниманием» в названии перекрасит
    # обычную строку результата.
    if low.startswith(("внимание", "! внимание")):
        return "warn"
    if stripped.startswith("===") or low.startswith("итог"):
        return "head"
    if set(stripped) <= set("=!-—") and len(stripped) > 2:
        return "head"

    if "→ да" in stripped:
        return "ok"
    if "не удалось проверить" in low:
        return "warn"
    if "→ нет" in stripped:
        return "bad"

    if "[работает, найдено]" in low:
        return "ok"
    if "[работает, не найдено]" in low:
        return "body"
    if "[не подошёл]" in low or "[не подошел]" in low:
        return "warn"

    if stripped.startswith(("[", "…", "...", "(")) or line.startswith("  "):
        return "muted"
    return "body"
