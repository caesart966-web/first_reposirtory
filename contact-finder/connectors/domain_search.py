"""Уровень D. Поиск домена компании через официальные search-API.

Никакого парсинга HTML поисковой выдачи (ТЗ, раздел 3D) — только официальные
API по ключам из .env:
- Google Programmable Search (GOOGLE_SEARCH_API_KEY + GOOGLE_SEARCH_CX);
- Яндекс Поиск для сайта / Search API (YANDEX_SEARCH_API_KEY + YANDEX_SEARCH_FOLDER_ID).

Запрос: «<название> <ИНН> официальный сайт». Из выдачи убираются агрегаторы
(rusprofile, sbis и т.п. — стоп-лист в config.yaml). Кандидат проверяется
WHOIS-сопоставлением и помечается как «предположительный»: подтверждённым
домен станет только после того, как коннектор website найдёт на сайте тот же
ИНН или название (иначе остаётся кандидатом с пониженным скорингом).
"""
from __future__ import annotations

import base64
import re
from typing import Optional
from urllib.parse import urlsplit
from xml.etree import ElementTree

from connectors.base import BaseConnector, register_connector
from connectors.whois_check import org_matches_company, whois_lookup
from core.models import Company, ConnectorResult, SourceLevel
from utils.http import FetchError

_GOOGLE_URL = "https://www.googleapis.com/customsearch/v1"
_YANDEX_URL = "https://yandex.ru/search/xml"


@register_connector
class DomainSearchConnector(BaseConnector):
    """Подбор домена, когда сайт компании неизвестен."""

    name = "domain_search"
    title = "Поиск домена (search API)"
    level = SourceLevel.D
    default_priority = 70

    def can_run(self, company: Company) -> bool:
        if company.website or company.website_candidate:
            return False   # сайт уже есть — искать нечего
        if not self.company_query_name(company):
            return False
        return self._google_ready() or self._yandex_ready()

    @property
    def enabled(self) -> bool:
        if not self.config.source_enabled(self.name):
            return False
        return self._google_ready() or self._yandex_ready()

    def missing_key_note(self) -> Optional[str]:
        if not (self._google_ready() or self._yandex_ready()):
            return ("нет ключей search API (GOOGLE_SEARCH_API_KEY+GOOGLE_SEARCH_CX "
                    "или YANDEX_SEARCH_API_KEY+YANDEX_SEARCH_FOLDER_ID в .env)")
        return None

    def _google_ready(self) -> bool:
        return bool(self.config.env("GOOGLE_SEARCH_API_KEY")
                    and self.config.env("GOOGLE_SEARCH_CX"))

    def _yandex_ready(self) -> bool:
        return bool(self.config.env("YANDEX_SEARCH_API_KEY")
                    and self.config.env("YANDEX_SEARCH_FOLDER_ID"))

    # ------------------------------------------------------------------ #

    async def fetch(self, company: Company) -> ConnectorResult:
        name = self.company_query_name(company)
        assert name is not None
        query = f'"{name}" {company.inn or ""} официальный сайт'.strip()

        links: list[str] = []
        if self._google_ready():
            try:
                links = await self._google_search(query)
            except FetchError as exc:
                self.log.debug("[%s] Google CSE недоступен: %s", company.key, exc)
        if not links and self._yandex_ready():
            try:
                links = await self._yandex_search(query)
            except FetchError as exc:
                self.log.debug("[%s] Yandex Search API недоступен: %s", company.key, exc)

        if not links:
            return ConnectorResult(ok=True, error="поисковая выдача пуста")

        candidate = self._pick_candidate(links)
        if candidate is None:
            return ConnectorResult(ok=True,
                                   error="в выдаче только агрегаторы/справочники")

        # WHOIS: домен принадлежит этому же юрлицу? (только сигнал, не приговор)
        whois_info = await whois_lookup(candidate)
        whois_match = org_matches_company(whois_info, company.name_full or name)

        url = f"https://{candidate}"
        self.log.info("[%s] Найден предположительный домен: %s (WHOIS org %s)",
                      company.key, candidate,
                      "совпал" if whois_match else "не совпал/нет данных")
        return ConnectorResult(
            company_updates={"website_candidate": url},
            source_urls=[url],
        )

    # ------------------------------------------------------------------ #

    async def _google_search(self, query: str) -> list[str]:
        resp = await self.http.fetch(
            _GOOGLE_URL,
            params={
                "key": self.config.env("GOOGLE_SEARCH_API_KEY"),
                "cx": self.config.env("GOOGLE_SEARCH_CX"),
                "q": query,
                "num": "10",
                "hl": "ru",
            },
            use_cache=True,
        )
        if resp.status in (401, 403):
            raise FetchError(f"Google CSE: ключ отклонён (HTTP {resp.status})",
                             url=_GOOGLE_URL, status=resp.status)
        if not resp.ok:
            raise FetchError(f"Google CSE вернул HTTP {resp.status}",
                             url=_GOOGLE_URL, status=resp.status,
                             retry_later=resp.status >= 500 or resp.status == 429)
        try:
            items = resp.json().get("items") or []
        except (ValueError, AttributeError):
            return []
        return [item.get("link") for item in items if item.get("link")]

    async def _yandex_search(self, query: str) -> list[str]:
        """Yandex Search API (XML-выдача, официальный интерфейс)."""
        resp = await self.http.fetch(
            _YANDEX_URL,
            params={
                "folderid": self.config.env("YANDEX_SEARCH_FOLDER_ID"),
                "apikey": self.config.env("YANDEX_SEARCH_API_KEY"),
                "query": query,
                "l10n": "ru",
                "filter": "none",
            },
            use_cache=True,
        )
        if resp.status in (401, 403):
            raise FetchError(f"Yandex Search API: ключ отклонён (HTTP {resp.status})",
                             url=_YANDEX_URL, status=resp.status)
        if not resp.ok:
            raise FetchError(f"Yandex Search API вернул HTTP {resp.status}",
                             url=_YANDEX_URL, status=resp.status,
                             retry_later=resp.status >= 500 or resp.status == 429)
        text = resp.text
        # Ответ может прийти в base64 (API v2) или сразу XML
        if "<yandexsearch" not in text and "<response" not in text:
            try:
                text = base64.b64decode(text).decode("utf-8", errors="replace")
            except (ValueError, UnicodeError):
                pass
        try:
            root = ElementTree.fromstring(text)
        except ElementTree.ParseError:
            return []
        return [el.text.strip() for el in root.iter("url")
                if el.text and el.text.strip()]

    # ------------------------------------------------------------------ #

    def _pick_candidate(self, links: list[str]) -> Optional[str]:
        """Первый домен выдачи, не входящий в стоп-лист агрегаторов."""
        stoplist = [d.lower() for d in
                    self.config.get("validation.aggregator_domains", [])]
        for link in links:
            host = urlsplit(link).netloc.lower().removeprefix("www.")
            if not host or ":" in host:
                continue
            if any(host == s or host.endswith("." + s) for s in stoplist):
                continue
            # поддомены крупных платформ-конструкторов тоже пропускаем
            if re.search(r"\.(narod|ucoz|nethouse|tilda)\.(ru|ws|cc)$", host):
                continue
            return host
        return None
