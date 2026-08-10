"""Уровень C. Яндекс.Карты — API Поиска по организациям (официальный, по ключу).

Ключ YANDEX_MAPS_API_KEY выдаётся в кабинете разработчика Яндекса.
Карточка засчитывается только при совпадении названия организации.
"""
from __future__ import annotations

from typing import Any, Optional

from connectors.base import BaseConnector, register_connector
from core.models import Company, ConnectorResult, Contact, ContactType, SourceLevel
from utils.http import FetchError
from validators.phone import normalize_phone

_API_URL = "https://search-maps.yandex.ru/v1/"


@register_connector
class YandexMapsConnector(BaseConnector):
    """Поиск организаций Яндекс.Карт."""

    name = "yandex_maps"
    title = "Яндекс.Карты"
    level = SourceLevel.C
    default_priority = 55
    needs_api_key = "YANDEX_MAPS_API_KEY"

    def can_run(self, company: Company) -> bool:
        return bool(self.company_query_name(company))

    async def fetch(self, company: Company) -> ConnectorResult:
        name = self.company_query_name(company)
        assert name is not None
        query = name if not company.region else f"{name} {company.region}"

        resp = await self.http.fetch(
            _API_URL,
            params={
                "text": query,
                "type": "biz",
                "lang": "ru_RU",
                "results": "5",
                "apikey": self.config.env(self.needs_api_key),
            },
            use_cache=True,
        )
        if resp.status in (401, 403):
            return ConnectorResult.failed(
                f"Яндекс.Карты: ключ API отклонён (HTTP {resp.status})")
        if not resp.ok:
            raise FetchError(f"Яндекс.Карты вернули HTTP {resp.status}",
                             url=_API_URL, status=resp.status,
                             retry_later=resp.status >= 500 or resp.status == 429)
        try:
            payload = resp.json()
        except ValueError:
            return ConnectorResult.failed("Яндекс.Карты: ответ не JSON")

        meta = self._pick_company(company, payload.get("features") or [])
        if meta is None:
            return ConnectorResult(ok=True, error="организация не найдена в Яндекс.Картах")

        contacts: list[Contact] = []
        updates: dict[str, Any] = {}
        card_url = meta.get("url") or "https://yandex.ru/maps/"

        for phone_entry in meta.get("Phones") or []:
            raw = str(phone_entry.get("formatted") or "").strip()
            normalized = normalize_phone(raw)
            if normalized:
                contacts.append(Contact(
                    type=ContactType.PHONE, value=normalized, raw=raw,
                    source=self.name, source_url="https://yandex.ru/maps/",
                    level=self.level,
                ))
        site = meta.get("url")
        if isinstance(site, str) and site.strip():
            url = site.strip()
            contacts.append(Contact(
                type=ContactType.WEBSITE, value=url, raw=url,
                source=self.name, source_url="https://yandex.ru/maps/",
                level=self.level,
            ))
            if not company.website:
                updates["website_candidate"] = url
        if isinstance(meta.get("address"), str) and not company.address:
            updates["address"] = meta["address"]

        if not contacts:
            return ConnectorResult(ok=True, error="в карточке Яндекс.Карт нет контактов")
        return ConnectorResult(contacts=contacts, company_updates=updates,
                               source_urls=[card_url])

    def _pick_company(self, company: Company, features: list[dict]) -> Optional[dict]:
        target = self.company_query_name(company) or ""
        for feature in features:
            meta = (feature.get("properties") or {}).get("CompanyMetaData") or {}
            if meta and self.names_similar(target, meta.get("name")):
                return meta
        return None
