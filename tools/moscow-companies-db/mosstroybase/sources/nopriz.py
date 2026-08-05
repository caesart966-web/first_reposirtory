"""Проверка членства в проектно-изыскательских СРО: открытый реестр НОПРИЗ.

НОПРИЗ — национальное объединение изыскателей и проектировщиков, реестр
членов СРО в этой сфере (в отличие от НОСТРОЙ — строительные СРО). Поиск
по ИНН, без ключей и оплаты.

reestr.nopriz.ru использует ту же платформу и структуру URL, что и
reestr.nostroy.ru (`/sro/{id}/member/list`) — по всей видимости, оба
реестра сделаны одним подрядчиком. Логика этого модуля — прямая копия
`sro.py` (включая автоопределение формата фильтра по тем же причинам:
незнакомый фильтр реестр молча игнорирует и возвращает общий список).

Важно: по умолчанию членство в НОПРИЗ НЕ используется для отсечения
компаний из выгрузок (в отличие от НОСТРОЙ) — это только информационная
проверка по явному запросу (`enrich-nopriz`/`check-nopriz`), в это поле
она не влияет на выгрузки/`daily`.
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime, timedelta
from typing import Any, Iterator

import requests

REJOIN_BAN_DAYS = 365

NOPRIZ_URL = "https://reestr.nopriz.ru/api/sro/all/member/list"

_FILTER_BODIES = (
    lambda inn: {"filters": {"inn": inn}, "page": 1, "pageSize": 20},
    lambda inn: {"filters": {"member": {"inn": inn}}, "page": 1, "pageSize": 20},
    lambda inn: {"searchString": inn, "page": 1, "pageSize": 20},
    lambda inn: {"filters": {}, "searchString": inn, "page": 1, "pageSize": 20},
    lambda inn: {"filters": {"member_inn": inn}, "page": 1, "pageSize": 20},
)

_working_body: int | None = None
_format_unusable: bool = False

_FORMER_MARKERS = ("исключ", "прекращ")


def _strings(obj: Any) -> Iterator[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _strings(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _strings(item)


def _find_records(payload: Any, inn: str) -> list[dict]:
    """Словари в ответе, среди значений которых встречается ровно наш ИНН."""
    records: list[dict] = []

    def rec(obj: Any) -> None:
        if isinstance(obj, dict):
            plain = [v for v in obj.values() if isinstance(v, (str, int))]
            if any(str(v).strip() == inn for v in plain):
                records.append(obj)
            for value in obj.values():
                rec(value)
        elif isinstance(obj, list):
            for item in obj:
                rec(item)

    rec(payload)
    return records


def _record_list(payload: Any) -> list[dict]:
    """Список записей из ответа реестра (обёртка data → data)."""
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, dict):
        data = data.get("data")
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def _is_former(record: dict) -> bool:
    return any(
        marker in text.lower() for text in _strings(record) for marker in _FORMER_MARKERS
    )


def _parse_date(text: str) -> date | None:
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", text.strip())
    if m:
        day, month, year = map(int, m.groups())
    else:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text.strip())
        if not m:
            return None
        year, month, day = map(int, m.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


_EXCLUSION_KEY_HINTS = ("stop", "прекращ", "исключ", "excl")
_FALLBACK_KEY_HINTS = ("last_updated",)


def _extract_exclusion_date(record: dict) -> date | None:
    for hints in (_EXCLUSION_KEY_HINTS, _FALLBACK_KEY_HINTS):
        found: list[date] = []

        def rec(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and any(h in key.lower() for h in hints):
                        parsed = _parse_date(value)
                        if parsed:
                            found.append(parsed)
                    elif isinstance(value, (dict, list)):
                        rec(value)
            elif isinstance(obj, list):
                for item in obj:
                    rec(item)

        rec(record)
        if found:
            return max(found)
    return None


def evaluate(payload: Any, inn: str) -> str | None:
    """None — записей нет; 'member' — состоит; 'former' — исключён/бывший."""
    records = _find_records(payload, inn)
    if not records:
        return None
    if all(_is_former(r) for r in records):
        return "former"
    return "member"


def _post(body: dict, session: requests.Session, timeout: int) -> Any | None:
    try:
        resp = session.post(NOPRIZ_URL, json=body, timeout=timeout)
        if resp.status_code != 200:
            return None
        return resp.json()
    except (requests.RequestException, ValueError):
        return None


def _former_verdict(matching: list[dict]) -> dict:
    """Вердикт для исключённых: свежие (< года) отсекаются, давние — лиды."""
    dates = [d for d in (_extract_exclusion_date(r) for r in matching) if d]
    excl_date = max(dates) if dates else None
    if excl_date is None:
        return {"nopriz_member": 0,
                "nopriz_info": ["НОПРИЗ: исключён, дата неизвестна — проверьте вручную"]}
    if (date.today() - excl_date).days < REJOIN_BAN_DAYS:
        until = excl_date + timedelta(days=REJOIN_BAN_DAYS)
        return {"nopriz_member": 1,
                "nopriz_info": [f"НОПРИЗ: исключён {excl_date:%d.%m.%Y}, вступление "
                                 f"не раньше {until:%d.%m.%Y}"]}
    return {"nopriz_member": 0,
            "nopriz_info": [f"НОПРИЗ: исключён {excl_date:%d.%m.%Y}, год прошёл"]}


def check_membership(inn: str, session: requests.Session, timeout: int = 30) -> dict | None:
    """{'nopriz_member': 1|0, 'nopriz_info': [...]} или None (недоступно/не определить).

    В отличие от sro.check_membership, это чисто информационная проверка —
    не используется для отсечения компаний из выгрузок по умолчанию.
    """
    global _working_body, _format_unusable
    if _format_unusable:
        return None

    order = list(range(len(_FILTER_BODIES)))
    if _working_body is not None:
        order.remove(_working_body)
        order.insert(0, _working_body)

    reachable = False
    for idx in order:
        payload = _post(_FILTER_BODIES[idx](inn), session, timeout)
        if payload is None:
            continue
        reachable = True
        records = _record_list(payload)
        matching = [r for r in records if _find_records(r, inn)]
        if matching:
            _working_body = idx
            if all(_is_former(r) for r in matching):
                return _former_verdict(matching)
            return {"nopriz_member": 1, "nopriz_info": ["НОПРИЗ: член СРО"]}
        if not records:
            # Пустой ответ = фильтр сработал, ИНН в реестре нет
            _working_body = idx
            return {"nopriz_member": 0, "nopriz_info": []}
        # Непустой список чужих записей — фильтр проигнорирован, пробуем другой

    if not reachable:
        return None
    _format_unusable = True
    print("[nopriz] реестр НОПРИЗ отвечает, но фильтр по ИНН не сработал ни в одном "
          "из известных форматов — проверка отключена до следующего запуска. "
          "Выполните check-nopriz и пришлите вывод разработчику.", file=sys.stderr)
    return None
