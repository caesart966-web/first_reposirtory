"""Нормализация и извлечение контактов (телефоны, e-mail) из текста."""

from __future__ import annotations

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")

# +7/8/7, затем 10 цифр с любыми скобками/дефисами/пробелами между группами.
# (?<!\d) запрещает начинать матч из середины длинного числа (id счётчиков
# и т.п. в коде страниц давали ложные «телефоны»)
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+7|8|7)[\s\-.(]*\d{3}[\s\-.)]*\d{3}[\s\-.]*\d{2}[\s\-.]*\d{2}(?!\d)"
)

# Первые цифры реальных российских кодов (гео 3xx/4xx/8xx, мобильные 9xx)
_VALID_CODE_STARTS = "3489"

# Мусорные "адреса" из вёрстки сайтов: logo@2x.png и т.п.
_JUNK_EMAIL_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".css", ".js", ".woff", ".woff2", ".ttf",
)


def extract_emails(text: str) -> list[str]:
    """Все e-mail из текста: нижний регистр, без дублей, без мусора из вёрстки."""
    found: list[str] = []
    for raw in EMAIL_RE.findall(text or ""):
        email = raw.lower().strip(".")
        if email.endswith(_JUNK_EMAIL_SUFFIXES):
            continue
        if email not in found:
            found.append(email)
    return found


def normalize_phone(raw: str) -> str | None:
    """Приводит российский номер к виду +7XXXXXXXXXX; иначе None."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits[0] in "78":
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        digits = "7" + digits
    else:
        return None
    # Код должен начинаться как настоящий российский (3xx/4xx/8xx/9xx)
    if digits[1] not in _VALID_CODE_STARTS:
        return None
    # Отсекаем заведомо фиктивные номера-заглушки
    if digits[1:] in {"0000000000", "1234567890", "9999999999"}:
        return None
    return "+" + digits


def is_valid_phone(phone: str) -> bool:
    """Годится ли уже сохранённый номер по текущим правилам (для выгрузок)."""
    return normalize_phone(phone) == phone


def extract_phones(text: str) -> list[str]:
    """Все телефоны из текста в нормализованном виде +7XXXXXXXXXX, без дублей."""
    found: list[str] = []
    for raw in PHONE_RE.findall(text or ""):
        phone = normalize_phone(raw)
        if phone and phone not in found:
            found.append(phone)
    return found


def merge_unique(*lists: list[str] | None) -> list[str]:
    """Объединяет списки строк, сохраняя порядок и убирая дубли/пустые."""
    merged: list[str] = []
    for lst in lists:
        for item in lst or []:
            item = (item or "").strip()
            if item and item not in merged:
                merged.append(item)
    return merged
