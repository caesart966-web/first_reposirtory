"""Деобфускация e-mail адресов, спрятанных от простых парсеров.

Примеры, которые приводим к нормальному виду:
    info (at) firma.ru       -> info@firma.ru
    sales[собака]zavod.рф    -> sales@zavod.рф
    op (a) stroy [точка] ru  -> op@stroy.ru
Картинки с адресами не распознаём (по ТЗ — пропускаем).
"""
from __future__ import annotations

import re

# «Собака» в разных написаниях: (at), [at], {at}, (а), [собака], " at ", " собака "
_AT_BRACKETED = re.compile(
    r"[\(\[\{]\s*(?:at|а|a|собака|dog|эт)\s*[\)\]\}]",
    re.IGNORECASE,
)
_AT_SPACED = re.compile(
    r"(?<=[\w.\-])\s+(?:at|собака)\s+(?=[\w])",
    re.IGNORECASE,
)

# «Точка»: (dot), [dot], (точка), " dot ", " точка "
_DOT_BRACKETED = re.compile(
    r"[\(\[\{]\s*(?:dot|точка|тчк)\s*[\)\]\}]",
    re.IGNORECASE,
)
_DOT_SPACED = re.compile(
    r"(?<=[\w\-])\s+(?:dot|точка)\s+(?=[\w])",
    re.IGNORECASE,
)

# Пробелы вокруг @ и точки внутри адреса: "info @ firma . ru"
_SPACES_AROUND_AT = re.compile(r"(?<=[\w.\-])\s*@\s*(?=[\w])")
_SPACES_AROUND_DOT = re.compile(r"(?<=[\w\-])\s*\.\s*(?=[a-zа-яё\d])", re.IGNORECASE)


def deobfuscate_text(text: str) -> str:
    """Заменить обфусцированные @ и точки, не трогая обычный текст."""
    if not text:
        return text
    out = _AT_BRACKETED.sub("@", text)
    out = _AT_SPACED.sub("@", out)
    out = _DOT_BRACKETED.sub(".", out)
    out = _DOT_SPACED.sub(".", out)
    # схлопываем пробелы только в окрестности уже найденной @
    if "@" in out:
        out = _SPACES_AROUND_AT.sub("@", out)
        # точки поджимаем только в «хвосте» после @, чтобы не портить предложения
        def _tighten(match: re.Match[str]) -> str:
            fragment = match.group(0)
            return _SPACES_AROUND_DOT.sub(".", fragment)

        out = re.sub(r"@[\w\-]+(?:\s*\.\s*[\w\-]+)+", _tighten, out)
    return out
