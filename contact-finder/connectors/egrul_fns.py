"""Уровень A. ФНС / ЕГРЮЛ: реквизиты, статус, адрес, руководитель.

Основной канал — публичный поиск https://egrul.nalog.ru (тот же, что на сайте
ФНС, без ключа). Резервный — открытое зеркало наборов ЕГРЮЛ (egrul.itsoft.ru),
отдающее полный JSON выписки по ИНН.

Прямых контактов (почта/телефон) в ЕГРЮЛ почти нет, но коннектор заполняет
карточку компании: полное/краткое наименование, ОГРН, статус, дату регистрации,
адрес, регион, руководителя — это база для остальных источников и скоринга.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from connectors.base import BaseConnector, register_connector
from core.models import Company, ConnectorResult, SourceLevel
from utils.http import FetchError

_EGRUL_URL = "https://egrul.nalog.ru/"
_EGRUL_RESULT_URL = "https://egrul.nalog.ru/search-result/{token}"
_ITSOFT_URL = "https://egrul.itsoft.ru/{inn}.json"

_REGION_RE = re.compile(
    r"(республика [\wё\- ]+|[\wё\- ]+ (?:область|край|автономный округ|автономная область)|"
    r"г\.? ?(?:москва|санкт-петербург|севастополь))",
    re.IGNORECASE,
)


def extract_region(address: str) -> Optional[str]:
    """Вытащить субъект РФ из строки юридического адреса."""
    if not address:
        return None
    m = _REGION_RE.search(address)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(0)).strip(" ,").title()


@register_connector
class EgrulConnector(BaseConnector):
    """Открытые данные ЕГРЮЛ (ФНС)."""

    name = "egrul"
    title = "ФНС ЕГРЮЛ"
    level = SourceLevel.A
    default_priority = 10

    def can_run(self, company: Company) -> bool:
        return bool(company.inn or company.ogrn or self.company_query_name(company))

    async def fetch(self, company: Company) -> ConnectorResult:
        query = company.inn or company.ogrn or self.company_query_name(company)
        assert query is not None

        updates: dict[str, Any] = {}
        source_url = _EGRUL_URL
        row = None
        try:
            row = await self._search_egrul(company, query)
        except FetchError as exc:
            self.log.debug("[%s] egrul.nalog.ru недоступен (%s), пробуем зеркало",
                           company.key, exc)

        if row is not None:
            updates = self._updates_from_egrul_row(row)
        elif company.inn:
            mirror = await self._search_itsoft(company.inn)
            if mirror is not None:
                updates = mirror
                source_url = _ITSOFT_URL.format(inn=company.inn)

        if not updates:
            return ConnectorResult(ok=True, company_updates={},
                                   error="компания не найдена в ЕГРЮЛ")

        return ConnectorResult(company_updates=updates, source_urls=[source_url])

    # ------------------------------------------------------------------ #

    async def _search_egrul(self, company: Company, query: str) -> Optional[dict]:
        """POST-поиск на egrul.nalog.ru: сначала токен, потом строки выдачи."""
        resp = await self.http.fetch(
            _EGRUL_URL, method="POST",
            data={"vyp3CaptchaToken": "", "page": "", "query": query, "region": ""},
            headers={"Accept": "application/json"},
            use_cache=True,
        )
        if not resp.ok:
            raise FetchError(f"egrul поиск вернул HTTP {resp.status}",
                             url=_EGRUL_URL, status=resp.status,
                             retry_later=resp.status in (429, 500, 502, 503))
        try:
            token = resp.json().get("t")
        except (ValueError, AttributeError):
            token = None
        if not token:
            raise FetchError("egrul не выдал токен поиска (возможно, капча)",
                             url=_EGRUL_URL)

        result = await self.http.fetch(
            _EGRUL_RESULT_URL.format(token=token),
            headers={"Accept": "application/json"},
            use_cache=True,
        )
        if not result.ok:
            raise FetchError(f"egrul выдача вернула HTTP {result.status}",
                             url=result.url, status=result.status)
        try:
            rows = result.json().get("rows") or []
        except ValueError:
            rows = []

        return self._pick_row(company, rows)

    def _pick_row(self, company: Company, rows: list[dict]) -> Optional[dict]:
        """Выбрать строку выдачи: по ИНН/ОГРН — точно, по имени — осторожно."""
        if not rows:
            return None
        if company.inn:
            for r in rows:
                if str(r.get("i", "")).strip() == company.inn:
                    return r
            return None
        if company.ogrn:
            for r in rows:
                if str(r.get("o", "")).strip() == company.ogrn:
                    return r
            return None
        # Поиск по названию: берём только уверенное совпадение,
        # предпочитая действующие организации (без даты прекращения "e")
        name = self.company_query_name(company) or ""
        matches = [r for r in rows if self.names_similar(name, r.get("n") or r.get("c"))]
        if not matches:
            return None
        active = [r for r in matches if not r.get("e")]
        pool = active or matches
        if len(pool) > 1:
            self.log.info("[%s] ЕГРЮЛ: %d похожих компаний по названию — пропускаем "
                          "(нужен ИНН для точности)", company.key, len(pool))
            return None
        return pool[0]

    def _updates_from_egrul_row(self, row: dict) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if row.get("i"):
            updates["inn"] = str(row["i"]).strip()
        if row.get("o"):
            updates["ogrn"] = str(row["o"]).strip()
        if row.get("n"):
            updates["name_full"] = str(row["n"]).strip()
        if row.get("c"):
            updates["name_short"] = str(row["c"]).strip()
        address = str(row.get("a") or "").strip()
        if address:
            updates["address"] = address
            region = extract_region(address)
            if region:
                updates["region"] = region
        # "g" — строка вида «ГЕНЕРАЛЬНЫЙ ДИРЕКТОР: ИВАНОВ ИВАН ИВАНОВИЧ»
        head = str(row.get("g") or "").strip()
        if head and ":" in head:
            position, _, fio = head.partition(":")
            updates["director_position"] = position.strip().capitalize()
            updates["director_name"] = fio.strip().title()
        if row.get("r"):
            updates["reg_date"] = str(row["r"]).strip()
        updates["entity_status"] = "ликвидировано" if row.get("e") else "действующее"
        return updates

    # ------------------------------------------------------------------ #

    async def _search_itsoft(self, inn: str) -> Optional[dict[str, Any]]:
        """Резерв: зеркало открытых данных ЕГРЮЛ (полный JSON выписки)."""
        try:
            resp = await self.http.fetch(_ITSOFT_URL.format(inn=inn), use_cache=True)
        except FetchError:
            return None
        if not resp.ok:
            return None
        try:
            data = resp.json()
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None

        updates: dict[str, Any] = {"inn": inn}
        doc = _find_first_dict(data, "СвЮЛ") or data

        attrs = doc.get("@attributes") or {}
        if attrs.get("ОГРН"):
            updates["ogrn"] = str(attrs["ОГРН"])
        if attrs.get("ДатаОГРН"):
            updates["reg_date"] = str(attrs["ДатаОГРН"])

        name_block = doc.get("СвНаимЮЛ") or {}
        name_attrs = name_block.get("@attributes") or {}
        if name_attrs.get("НаимЮЛПолн"):
            updates["name_full"] = str(name_attrs["НаимЮЛПолн"])
        short_block = name_block.get("СвНаимЮЛСокр") or {}
        short_attrs = short_block.get("@attributes") or {}
        if short_attrs.get("НаимСокр"):
            updates["name_short"] = str(short_attrs["НаимСокр"])

        addr = _find_first_dict(doc, "АдресРФ")
        if addr:
            updates["address"] = _flatten_address(addr)
            region = extract_region(updates["address"])
            if region:
                updates["region"] = region

        okved = _find_first_dict(doc, "СвОКВЭДОсн")
        if okved:
            ok_attrs = okved.get("@attributes") or {}
            code = ok_attrs.get("КодОКВЭД")
            title = ok_attrs.get("НаимОКВЭД")
            if code:
                updates["okved"] = f"{code} {title or ''}".strip()

        head = _find_first_dict(doc, "СвДолжнЛ") or _find_first_dict(doc, "СведДолжнФЛ")
        if head:
            fio_block = _find_first_dict(head, "СвФЛ") or {}
            fio_attrs = fio_block.get("@attributes") or {}
            fio = " ".join(filter(None, (
                fio_attrs.get("Фамилия"), fio_attrs.get("Имя"), fio_attrs.get("Отчество"),
            )))
            if fio:
                updates["director_name"] = fio.title()
            pos_block = _find_first_dict(head, "СвДолжн") or {}
            pos_attrs = pos_block.get("@attributes") or {}
            if pos_attrs.get("НаимДолжн"):
                updates["director_position"] = str(pos_attrs["НаимДолжн"]).capitalize()

        stopped = _find_first_dict(doc, "СвПрекрЮЛ")
        updates["entity_status"] = "ликвидировано" if stopped else "действующее"
        return updates


def _find_first_dict(obj: Any, key: str) -> Optional[dict]:
    """Найти первый словарь по ключу на любой глубине JSON-выписки."""
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], dict):
            return obj[key]
        if key in obj and isinstance(obj[key], list) and obj[key] and isinstance(obj[key][0], dict):
            return obj[key][0]
        for v in obj.values():
            found = _find_first_dict(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_first_dict(item, key)
            if found is not None:
                return found
    return None


def _flatten_address(addr: dict) -> str:
    """Собрать адрес из вложенных элементов выписки в одну строку."""
    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            attrs = node.get("@attributes")
            if isinstance(attrs, dict):
                for k in ("Индекс", "НаимРегион", "ТипНаселПункт", "НаимНаселПункт",
                          "НаимГород", "ТипУлица", "НаимУлица", "Дом", "Корпус", "Кварт"):
                    v = attrs.get(k)
                    if v and str(v) not in parts:
                        parts.append(str(v))
            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(addr)
    return ", ".join(parts)
