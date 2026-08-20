"""Поиск связанных компаний: общий директор, адрес или телефон.

Задача — найти пачки юрлиц, за которыми стоит один и тот же человек:
такие группы либо отсеиваются как технические, либо, наоборот, выводят
на реального бенефициара нескольких компаний.

Учредители сюда пока не входят: в базе их нет (Checko отдаёт их отдельным
блоком, который мы не извлекаем). Как появятся — добавятся ещё одним
признаком связи, структура для этого готова.

Важно про адреса. Реестр МСП даёт только регион/район/город — у всех
московских компаний адрес буквально «г. Москва». Связывать по такому
нельзя, иначе в одну группу попадёт вся база, поэтому в расчёт идут
только точные адреса (с домом или почтовым индексом) — их проставляет
Checko.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# Признаки точного адреса: почтовый индекс в начале или номер дома
_PRECISE_ADDRESS = re.compile(
    r"^\d{6},|\bд\.?\s*\d|\bдом\s*\d|\bстр\.?\s*\d|\bкорп\.?\s*\d|\bпомещ", re.I
)

# Слишком общие «адреса», которые встречаются у тысяч компаний
_COARSE_HINTS = ("г. москва", "г. санкт-петербург", "москва", "санкт-петербург")


def is_precise_address(address: str | None) -> bool:
    """Адрес пригоден для связывания только если указан дом/индекс."""
    text = (address or "").strip()
    if len(text) < 15 or not _PRECISE_ADDRESS.search(text):
        return False
    return text.lower().strip(" ,.") not in _COARSE_HINTS


def normalize_name(fio: str | None) -> str:
    """ФИО к сравнимому виду: регистр, ё→е, лишние пробелы."""
    text = (fio or "").strip().lower().replace("ё", "е")
    return re.sub(r"\s+", " ", text)


def normalize_address(address: str | None) -> str:
    text = (address or "").strip().lower().replace("ё", "е")
    text = re.sub(r"\s+", " ", text)
    # Индекс в начале и пробелы после запятых не должны мешать сравнению
    text = re.sub(r"^\d{6},\s*", "", text)
    return text.strip(" ,.")


def _keys_of(company: dict) -> list[tuple[str, str]]:
    """Признаки связи одной компании: (тип, значение)."""
    keys: list[tuple[str, str]] = []

    director = normalize_name(company.get("director"))
    # ФИО без пробелов — мусор вроде «нет данных»; настоящее ФИО из 2-3 слов
    if director and 2 <= len(director.split()) <= 4:
        keys.append(("директор", director))

    address = company.get("address")
    if is_precise_address(address):
        keys.append(("адрес", normalize_address(address)))

    for field in ("phones", "phones_site"):
        for phone in company.get(field) or []:
            phone = (phone or "").strip()
            if phone:
                keys.append(("телефон", phone))

    return keys


class _Union:
    """Объединение компаний в группы (система непересекающихся множеств)."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, item: str) -> None:
        self.parent.setdefault(item, item)

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != root:      # путь сжимаем, чтобы не тормозило
            self.parent[item], item = root, self.parent[item]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def find_groups(
    companies: Iterable[dict],
    min_size: int = 2,
    kinds: tuple[str, ...] = ("директор", "адрес", "телефон"),
) -> list[dict[str, Any]]:
    """Группы связанных компаний.

    Возвращает список групп, отсортированный по размеру (сначала крупные).
    Каждая группа: {'inns': [...], 'reasons': [(тип, значение, сколько), ...]}.
    Компании связываются транзитивно: если A и B делят директора, а B и C —
    адрес, все трое попадут в одну группу.
    """
    companies = [c for c in companies if (c.get("inn") or "").strip()]
    by_key: dict[tuple[str, str], list[str]] = {}
    union = _Union()

    for company in companies:
        inn = company["inn"]
        union.add(inn)
        for kind, value in _keys_of(company):
            if kind in kinds:
                by_key.setdefault((kind, value), []).append(inn)

    for (_kind, _value), inns in by_key.items():
        if len(inns) < 2:
            continue
        first = inns[0]
        for other in inns[1:]:
            union.union(first, other)

    grouped: dict[str, list[str]] = {}
    for company in companies:
        grouped.setdefault(union.find(company["inn"]), []).append(company["inn"])

    # Причины раскладываем по группам одним проходом: все компании с общим
    # ключом уже объединены, поэтому корень достаточно взять у первой.
    # (Перебор «каждая группа × все ключи» давал квадрат и минуты на 170 тыс.)
    reasons_by_root: dict[str, list[tuple[str, str, int]]] = {}
    for (kind, value), inns in by_key.items():
        unique = set(inns)
        if len(unique) < 2:
            continue
        root = union.find(next(iter(unique)))
        reasons_by_root.setdefault(root, []).append((kind, value, len(unique)))

    result: list[dict[str, Any]] = []
    for root, members in grouped.items():
        if len(members) < min_size:
            continue
        reasons = sorted(reasons_by_root.get(root, []), key=lambda r: -r[2])
        result.append({"inns": sorted(set(members)), "reasons": reasons})

    result.sort(key=lambda g: -len(g["inns"]))
    return result


def describe(reasons: list[tuple[str, str, int]], limit: int = 3) -> str:
    """Короткое человекочитаемое описание, почему компании связаны."""
    parts = [f"{kind}: {value} ({count})" for kind, value, count in reasons[:limit]]
    if len(reasons) > limit:
        parts.append(f"и ещё {len(reasons) - limit}")
    return "; ".join(parts)
