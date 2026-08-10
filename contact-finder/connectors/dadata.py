"""Уровень C. Dadata — сервис обогащения по ИНН с официальным API и тарифом.

Используется метод findById/party (подключается по ключу DADATA_API_KEY из .env).
Заполняет карточку компании (статус, адрес, ОКВЭД, руководитель) и, если тариф
отдаёт, контактные телефоны и почты.
"""
from __future__ import annotations

from typing import Any

from connectors.base import BaseConnector, register_connector
from core.models import Company, ConnectorResult, Contact, ContactType, SourceLevel
from utils.http import FetchError
from validators.email import extract_emails
from validators.phone import normalize_phone

_API_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"


@register_connector
class DadataConnector(BaseConnector):
    """Обогащение по ИНН через Dadata."""

    name = "dadata"
    title = "Dadata"
    level = SourceLevel.C
    default_priority = 60
    needs_api_key = "DADATA_API_KEY"

    def can_run(self, company: Company) -> bool:
        return bool(company.inn or company.ogrn)

    async def fetch(self, company: Company) -> ConnectorResult:
        query = company.inn or company.ogrn
        assert query is not None
        resp = await self.http.fetch(
            _API_URL, method="POST",
            json_body={"query": query, "count": 5},
            headers={
                "Authorization": f"Token {self.config.env(self.needs_api_key)}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            use_cache=True,
        )
        if resp.status in (401, 403):
            return ConnectorResult.failed(f"Dadata: ключ API отклонён (HTTP {resp.status})")
        if not resp.ok:
            raise FetchError(f"Dadata вернула HTTP {resp.status}", url=_API_URL,
                             status=resp.status,
                             retry_later=resp.status >= 500 or resp.status == 429)
        try:
            suggestions = resp.json().get("suggestions") or []
        except (ValueError, AttributeError):
            return ConnectorResult.failed("Dadata: ответ не JSON")

        data = None
        for s in suggestions:
            d = s.get("data") or {}
            if company.inn and d.get("inn") == company.inn:
                data = d
                break
            if company.ogrn and d.get("ogrn") == company.ogrn:
                data = d
                break
        if data is None and len(suggestions) == 1:
            data = suggestions[0].get("data") or {}
        if not data:
            return ConnectorResult(ok=True, error="компания не найдена в Dadata")

        updates = self._updates_from_party(data)
        contacts = self._contacts_from_party(data)
        return ConnectorResult(contacts=contacts, company_updates=updates,
                               source_urls=["https://dadata.ru/api/find-party/"])

    # ------------------------------------------------------------------ #

    @staticmethod
    def _updates_from_party(data: dict) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        if data.get("inn"):
            updates["inn"] = str(data["inn"])
        if data.get("ogrn"):
            updates["ogrn"] = str(data["ogrn"])
        name = data.get("name") or {}
        if name.get("full_with_opf"):
            updates["name_full"] = name["full_with_opf"]
        if name.get("short_with_opf"):
            updates["name_short"] = name["short_with_opf"]
        state = data.get("state") or {}
        status = str(state.get("status") or "").upper()
        if status:
            updates["entity_status"] = (
                "действующее" if status == "ACTIVE" else "ликвидировано"
            )
        reg_ts = state.get("registration_date")
        if isinstance(reg_ts, (int, float)) and reg_ts > 0:
            from datetime import datetime, timezone
            updates["reg_date"] = datetime.fromtimestamp(
                reg_ts / 1000, tz=timezone.utc).strftime("%d.%m.%Y")
        address = data.get("address") or {}
        if address.get("value"):
            updates["address"] = address["value"]
        addr_data = address.get("data") or {}
        if addr_data.get("region_with_type"):
            updates["region"] = addr_data["region_with_type"]
        if data.get("okved"):
            updates["okved"] = str(data["okved"])
        management = data.get("management") or {}
        if management.get("name"):
            updates["director_name"] = str(management["name"]).title()
        if management.get("post"):
            updates["director_position"] = str(management["post"]).capitalize()
        return updates

    def _contacts_from_party(self, data: dict) -> list[Contact]:
        contacts: list[Contact] = []
        source_url = "https://dadata.ru/api/find-party/"
        for entry in data.get("emails") or []:
            raw = entry if isinstance(entry, str) else str(
                (entry.get("data") or {}).get("source") or entry.get("value") or "")
            for email in extract_emails(raw):
                contacts.append(Contact(
                    type=ContactType.EMAIL, value=email, raw=raw,
                    source=self.name, source_url=source_url, level=self.level,
                ))
        for entry in data.get("phones") or []:
            raw = entry if isinstance(entry, str) else str(
                (entry.get("data") or {}).get("source") or entry.get("value") or "")
            normalized = normalize_phone(raw)
            if normalized:
                contacts.append(Contact(
                    type=ContactType.PHONE, value=normalized, raw=raw,
                    source=self.name, source_url=source_url, level=self.level,
                ))
        return contacts
