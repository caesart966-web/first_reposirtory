"""Уровень C. 2ГИС Catalog API (официальный, по ключу DGIS_API_KEY из .env).

Ищем карточку организации по названию и региону, забираем контакты из
contact_groups. Карточка засчитывается только при совпадении названия.
"""
from __future__ import annotations

from typing import Any, Optional

from connectors.base import BaseConnector, register_connector
from core.models import Company, ConnectorResult, Contact, ContactType, SourceLevel
from utils.http import FetchError
from validators.email import extract_emails
from validators.phone import normalize_phone

_API_URL = "https://catalog.api.2gis.com/3.0/items"


@register_connector
class DgisConnector(BaseConnector):
    """Справочник организаций 2ГИС."""

    name = "dgis"
    title = "2ГИС"
    level = SourceLevel.C
    default_priority = 50
    needs_api_key = "DGIS_API_KEY"

    def can_run(self, company: Company) -> bool:
        return bool(self.company_query_name(company))

    async def fetch(self, company: Company) -> ConnectorResult:
        name = self.company_query_name(company)
        assert name is not None
        query = name if not company.region else f"{name} {company.region}"

        resp = await self.http.fetch(
            _API_URL,
            params={
                "q": query,
                "fields": "items.contact_groups,items.name_ex,items.org,items.adm_div",
                "page_size": "5",
                "key": self.config.env(self.needs_api_key),
            },
            use_cache=True,
        )
        if resp.status == 403:
            return ConnectorResult.failed("2ГИС: ключ API отклонён (HTTP 403)")
        if not resp.ok:
            raise FetchError(f"2ГИС вернул HTTP {resp.status}", url=_API_URL,
                             status=resp.status, retry_later=resp.status >= 500)
        try:
            payload = resp.json()
        except ValueError:
            return ConnectorResult.failed("2ГИС: ответ не JSON")

        items = (payload.get("result") or {}).get("items") or []
        item = self._pick_item(company, items)
        if item is None:
            return ConnectorResult(ok=True, error="организация не найдена в 2ГИС")

        contacts = self._contacts_from_item(item)
        updates: dict[str, Any] = {}
        for c in contacts:
            if c.type == ContactType.WEBSITE and not company.website:
                updates["website_candidate"] = c.value
        if not contacts:
            return ConnectorResult(ok=True, error="в карточке 2ГИС нет контактов")
        return ConnectorResult(contacts=contacts, company_updates=updates,
                               source_urls=["https://2gis.ru/"])

    # ------------------------------------------------------------------ #

    def _pick_item(self, company: Company, items: list[dict]) -> Optional[dict]:
        target = self.company_query_name(company) or ""
        for item in items:
            candidates = [
                item.get("name"),
                (item.get("name_ex") or {}).get("primary"),
                (item.get("org") or {}).get("name"),
            ]
            if any(self.names_similar(target, c) for c in candidates if c):
                return item
        return None

    def _contacts_from_item(self, item: dict) -> list[Contact]:
        contacts: list[Contact] = []
        seen: set[tuple[str, str]] = set()
        for group in item.get("contact_groups") or []:
            for contact in group.get("contacts") or []:
                ctype = str(contact.get("type") or "").lower()
                value = str(contact.get("value") or contact.get("text") or "").strip()
                if not value:
                    continue
                if ctype == "phone":
                    normalized = normalize_phone(value)
                    if normalized and ("phone", normalized) not in seen:
                        seen.add(("phone", normalized))
                        contacts.append(Contact(
                            type=ContactType.PHONE, value=normalized, raw=value,
                            source=self.name, source_url="https://2gis.ru/",
                            level=self.level,
                        ))
                elif ctype == "email":
                    for email in extract_emails(value):
                        if ("email", email) not in seen:
                            seen.add(("email", email))
                            contacts.append(Contact(
                                type=ContactType.EMAIL, value=email, raw=value,
                                source=self.name, source_url="https://2gis.ru/",
                                level=self.level,
                            ))
                elif ctype == "website":
                    url = value if value.startswith("http") else "https://" + value
                    if ("website", url) not in seen:
                        seen.add(("website", url))
                        contacts.append(Contact(
                            type=ContactType.WEBSITE, value=url, raw=value,
                            source=self.name, source_url="https://2gis.ru/",
                            level=self.level,
                        ))
                elif ctype in ("telegram", "whatsapp", "viber"):
                    if ("messenger", value) not in seen:
                        seen.add(("messenger", value))
                        contacts.append(Contact(
                            type=ContactType.MESSENGER, value=value, raw=value,
                            source=self.name, source_url="https://2gis.ru/",
                            level=self.level, extra={"network": ctype},
                        ))
                elif ctype in ("vkontakte", "odnoklassniki", "youtube"):
                    if ("social", value) not in seen:
                        seen.add(("social", value))
                        contacts.append(Contact(
                            type=ContactType.SOCIAL, value=value, raw=value,
                            source=self.name, source_url="https://2gis.ru/",
                            level=self.level, extra={"network": ctype},
                        ))
        return contacts
