"""Проверка принадлежности к конкретной СРО.

Основной вопрос заказчика обычно звучит не «в каких СРО состоит компания»,
а «состоит ли она вот в этой». Ответ выносится отдельной колонкой.
"""

from __future__ import annotations

import re

#: Известные сокращения СРО -> как организация называется в реестре.
#: Короткая аббревиатура («ОРС») сама по себе ненадёжна: она встречается
#: внутри других слов, поэтому ищем ещё и полное наименование.
ALIASES: dict[str, tuple[str, ...]] = {
    "ОРС": ("объединение ростовских строителей",),
    "ОРПД": ("объединение ростовских проектировщиков",),
}

#: Три состояния ответа. «Не проверено» — не разновидность «нет».
YES = "Да"
NO = "Нет"
UNKNOWN = "не проверено"


def build_matcher(pattern: str):
    """Возвращает функцию «строка -> совпадает ли с искомой СРО».

    Аббревиатура из заглавных букв ищется по границам слова, иначе «ОРС»
    нашлось бы внутри «пОРСк» и любая СРО стала бы искомой. Длинные
    названия ищутся обычным вхождением — там ложных срабатываний нет.
    """
    parts: list[str] = []
    for raw in str(pattern or "").split("|"):
        token = raw.strip()
        if not token:
            continue
        if len(token) <= 6 and token.upper() == token:
            parts.append(rf"\b{re.escape(token)}\b")
        else:
            parts.append(re.escape(token))
        for alias in ALIASES.get(token.upper(), ()):
            parts.append(re.escape(alias))

    if not parts:
        return lambda text: False

    regex = re.compile("|".join(parts), re.IGNORECASE)
    return lambda text: bool(regex.search(str(text or "")))


def mark_target(rows: list[dict], pattern: str) -> list[dict]:
    """Проставляет ответ про искомую СРО — одинаковый для всех строк компании.

    Компания может состоять сразу в нескольких СРО и занимать несколько
    строк. Вопрос «состоит ли в ОРС» относится к компании целиком, поэтому
    ответ во всех её строках один и тот же.
    """
    matches = build_matcher(pattern)

    verdict: dict[str, str] = {}
    for row in rows:
        inn = row["inn"]
        if row.get("unchecked"):
            # Реестр не ответил — сказать «нет» нельзя, это не проверка.
            verdict.setdefault(inn, UNKNOWN)
            continue
        if matches(row.get("sro")) or matches(row.get("number")):
            verdict[inn] = YES
        else:
            verdict.setdefault(inn, NO)

    for row in rows:
        row["target"] = verdict.get(row["inn"], UNKNOWN)
    return rows
