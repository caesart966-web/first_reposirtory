"""
Выбор одного юридического адреса из уже сохранённого списка.

Нужен для пересборки адресов по кэшу: в файле состояния лежат разобранные
поля, а не сырые ответы API, поэтому путь в JSON — по которому адрес выбирает
``checko_api`` — здесь недоступен. Выбор идёт по содержимому строки:

* адрес СРО повторяется у сотен членов — он находится по частоте и отбрасывается;
* регион адреса сверяется с кодом региона в ИНН;
* современный формат ФИАС — признак юридического адреса из ЕГРЮЛ;
* старый формат КЛАДР («Санкт-Петербург г») приходит из выгрузки НОСТРОЙ,
  а не из checko.ru, и почти всегда оказывается адресом СРО.

Модуль ничего не запрашивает по сети и не расходует квоту.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Sequence

from .textutils import clean_text, tidy_address

#: Код региона в первых двух цифрах ИНН -> как регион пишется в адресе.
REGION_PATTERNS: dict[str, str] = {
    "01": r"адыге", "02": r"башкортостан", "03": r"буряти", "04": r"респ\w*\s+алтай",
    "05": r"дагестан", "06": r"ингушети", "07": r"кабардино-балкар", "08": r"калмыки",
    "09": r"карачаево-черкес", "10": r"карели", "11": r"коми", "12": r"марий\s+эл",
    "13": r"мордови", "14": r"саха|якути", "15": r"северная\s+осети", "16": r"татарстан",
    "17": r"тыва", "18": r"удмурт", "19": r"хакаси", "20": r"чеченск", "21": r"чувашск",
    "22": r"алтайский\s+кра", "23": r"краснодарский\s+кра", "24": r"красноярский\s+кра",
    "25": r"приморский\s+кра", "26": r"ставропольский\s+кра", "27": r"хабаровский\s+кра",
    "28": r"амурск", "29": r"архангельск", "30": r"астраханск", "31": r"белгородск",
    "32": r"брянск", "33": r"владимирск", "34": r"волгоградск", "35": r"вологод",
    "36": r"воронежск", "37": r"ивановск", "38": r"иркутск", "39": r"калининградск",
    "40": r"калужск", "41": r"камчатск", "42": r"кемеровск|кузбасс", "43": r"кировск",
    "44": r"костромск", "45": r"курганск", "46": r"курск", "47": r"ленинградск",
    "48": r"липецк", "49": r"магаданск", "50": r"московск\w*\s+обл", "51": r"мурманск",
    "52": r"нижегородск", "53": r"новгородск", "54": r"новосибирск", "55": r"омск",
    "56": r"оренбургск", "57": r"орловск", "58": r"пензенск", "59": r"пермск",
    "60": r"псковск", "61": r"ростовск", "62": r"рязанск", "63": r"самарск",
    "64": r"саратовск", "65": r"сахалинск", "66": r"свердловск", "67": r"смоленск",
    "68": r"тамбовск", "69": r"тверск", "70": r"томск", "71": r"тульск",
    "72": r"тюменск", "73": r"ульяновск", "74": r"челябинск", "75": r"забайкальск",
    "76": r"ярославск", "77": r"москва", "78": r"санкт-петербург", "79": r"еврейск",
    "80": r"донецк", "81": r"луганск", "82": r"крым", "83": r"ненецк",
    "84": r"херсонск", "85": r"запорожск", "86": r"ханты-мансийск|югра",
    "87": r"чукотск", "89": r"ямало-ненецк", "91": r"крым", "92": r"севастополь",
}
#: «Московская область» содержит тот же корень, что и «Москва», — разводим явно.
REGION_EXCLUDE: dict[str, str] = {"77": r"московск\w*\s+обл"}

#: Современный формат ФИАС — так юридический адрес отдаёт checko.ru.
_FIAS_MARKER_RE = re.compile(r"вн\.\s*тер\.\s*г\.", re.IGNORECASE)
#: Индекс в начале строки — признак полного адреса.
_POSTAL_PREFIX_RE = re.compile(r"^\s*\d{6}\b")
#: Старый формат КЛАДР: тип идёт после названия («Санкт-Петербург г»).
_LEGACY_KLADR_RE = re.compile(r"[А-Яа-яЁё]\s+(?:г|обл|край|респ|р-н)\s*,", re.IGNORECASE)

#: Доля карточек, начиная с которой одинаковый адрес считается адресом СРО.
SHARED_ADDRESS_SHARE = 0.15


def region_matches(address: str, inn: str) -> bool:
    """Совпадает ли регион в адресе с кодом региона в ИНН."""
    pattern = REGION_PATTERNS.get(str(inn or "")[:2])
    if not pattern:
        return False
    lowered = address.lower()
    exclude = REGION_EXCLUDE.get(str(inn)[:2])
    if exclude and re.search(exclude, lowered):
        return False
    return bool(re.search(pattern, lowered))


def score_address(address: str, inn: str) -> int:
    """Чем выше балл, тем вероятнее, что это юридический адрес компании."""
    score = 0
    if region_matches(address, inn):
        score += 100
    if _FIAS_MARKER_RE.search(address):
        score += 40
    if _POSTAL_PREFIX_RE.match(address):
        score += 10
    if _LEGACY_KLADR_RE.search(address):
        score -= 60
    # Подробный адрес (корпус, литера, помещение) вероятнее юридический,
    # чем обрывок вида «г. Мурманск».
    score += min(address.count(","), 8)
    return score


def detect_shared_addresses(
    address_lists: Iterable[Sequence[str]], min_share: float = SHARED_ADDRESS_SHARE
) -> set[str]:
    """Находит адреса, повторяющиеся у многих компаний, — это адреса СРО.

    Собственный адрес компании уникален. Адрес СРО одинаков у всех её членов,
    поэтому порог по доле карточек отсекает его без ручного списка.
    """
    lists = [list(item) for item in address_lists]
    counter: Counter[str] = Counter()
    for addresses in lists:
        for address in set(addresses):
            counter[address] += 1
    threshold = max(2, int(len(lists) * min_share))
    return {address for address, count in counter.items() if count >= threshold}


def pick_address(
    addresses: Sequence[str], inn: str, shared: frozenset[str] | set[str] = frozenset()
) -> tuple[str, bool]:
    """Возвращает (один адрес, признак неоднозначности).

    Неоднозначность означает, что два кандидата набрали одинаковый максимум:
    такую строку стоит уточнить запросом к checko.ru по полю ЮрАдрес.
    """
    candidates = [
        text for text in (clean_text(item) for item in addresses) if text and text not in shared
    ]
    if not candidates:
        return "", False
    if len(candidates) == 1:
        return tidy_address(candidates[0]), False

    scored = sorted(
        ((score_address(item, inn), item) for item in candidates), key=lambda pair: -pair[0]
    )
    ambiguous = scored[0][0] == scored[1][0]
    return tidy_address(scored[0][1]), ambiguous
