"""Нормализация и классификация российских телефонных номеров.

Целевой формат: +7XXXXXXXXXX. Типы: мобильный / городской / 8-800.
"""
from __future__ import annotations

import re
from typing import Optional

# Телефон в свободном тексте. Требуем «телефонный» префикс (+7 / 8 / 7 / скобку),
# чтобы не захватывать ИНН, ОГРН и прочие длинные числа.
PHONE_RE = re.compile(
    r"""
    (?<![\d\w])
    (?:\+?7|8)                       # префикс страны или межгород
    [\s .\-–—]*
    \(?\s*\d{3,5}\s*\)?              # код города/оператора
    [\s .\-–—]*
    \d{1,3}
    [\s .\-–—]*
    \d{2}
    [\s .\-–—]*
    \d{2}
    (?![\d])
    """,
    re.VERBOSE,
)

_MOBILE_PREFIX = "9"
_TOLL_FREE_CODES = ("800", "804")


def normalize_phone(raw: str) -> Optional[str]:
    """Привести номер к +7XXXXXXXXXX; None — если это не российский номер."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 11 and digits[0] in "78":
        digits = digits[1:]
    elif len(digits) == 10:
        pass
    else:
        return None
    # У российского номера код зоны не начинается с 0, 1, 2 или 7
    if digits[0] in "0127":
        return None
    return "+7" + digits


def phone_type(normalized: str) -> str:
    """Классификация номера: мобильный / 8-800 / городской."""
    if not normalized or not normalized.startswith("+7") or len(normalized) != 12:
        return "неизвестно"
    body = normalized[2:]
    if body.startswith(_MOBILE_PREFIX):
        return "мобильный"
    if body[:3] in _TOLL_FREE_CODES:
        return "8-800"
    return "городской"


def extract_phones(text: str) -> list[str]:
    """Найти и нормализовать все телефоны в тексте (без дубликатов)."""
    found: list[str] = []
    seen: set[str] = set()
    for match in PHONE_RE.finditer(text or ""):
        normalized = normalize_phone(match.group(0))
        if normalized and normalized not in seen:
            seen.add(normalized)
            found.append(normalized)
    return found


def format_phone_display(normalized: str) -> str:
    """+7XXXXXXXXXX -> +7 (XXX) XXX-XX-XX для человекочитаемого вывода."""
    if not normalized or len(normalized) != 12:
        return normalized or ""
    body = normalized[2:]
    return f"+7 ({body[0:3]}) {body[3:6]}-{body[6:8]}-{body[8:10]}"
