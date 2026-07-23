"""Проверка членства в строительных СРО: открытый реестр НОСТРОЙ.

НОСТРОЙ — единый реестр членов СРО в области строительства. Поиск по ИНН,
без ключей и оплаты. Компании, состоящие в строительной СРО, исключаются из
работы: им не тратится квота Checko и они не попадают в выгрузки (вернуть
можно флагом --include-sro).

Членство в проектно-изыскательских СРО (реестр НОПРИЗ) сознательно НЕ
проверяется — по условию задачи оно не является поводом отсечь компанию.

Формат ответа реестра может меняться, поэтому разбор устойчивый: записи
фильтруются по точному совпадению ИНН, статус определяется по текстовым
признакам («исключ…»/«прекращ…» = бывший член, не отсекаем).
"""

from __future__ import annotations

from typing import Any, Iterator

import requests

NOSTROY_URL = "https://reestr.nostroy.ru/api/sro/all/member/list"

# Варианты имени фильтра по ИНН в API реестра; записи в любом случае
# перепроверяются по точному ИНН, так что лишние результаты не страшны
_FILTER_KEYS = ("member_inn", "inn")

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


def _is_former(record: dict) -> bool:
    return any(
        marker in text.lower() for text in _strings(record) for marker in _FORMER_MARKERS
    )


def evaluate(payload: Any, inn: str) -> str | None:
    """None — записей нет; 'member' — состоит; 'former' — исключён/бывший."""
    records = _find_records(payload, inn)
    if not records:
        return None
    if all(_is_former(r) for r in records):
        return "former"
    return "member"


def _query(inn: str, session: requests.Session, timeout: int) -> Any | None:
    for filter_key in _FILTER_KEYS:
        try:
            resp = session.post(
                NOSTROY_URL,
                json={"filters": {filter_key: inn}, "page": 1, "pageSize": 20},
                timeout=timeout,
            )
            if resp.status_code != 200:
                continue
            return resp.json()
        except (requests.RequestException, ValueError):
            continue
    return None


def check_membership(inn: str, session: requests.Session, timeout: int = 30) -> dict | None:
    """{'sro_member': 1|0, 'sro_info': [...]} или None, если реестр недоступен.

    sro_member = 1 только для действующих членов строительной СРО (НОСТРОЙ);
    бывшие/исключённые члены не отсекаются, но помечаются в sro_info.
    """
    payload = _query(inn, session, timeout)
    if payload is None:
        return None  # реестр недоступен — пометим в другой раз
    verdict = evaluate(payload, inn)
    if verdict == "member":
        return {"sro_member": 1, "sro_info": ["НОСТРОЙ: член строительной СРО"]}
    if verdict == "former":
        return {"sro_member": 0, "sro_info": ["НОСТРОЙ: исключён/бывший член"]}
    return {"sro_member": 0, "sro_info": []}
