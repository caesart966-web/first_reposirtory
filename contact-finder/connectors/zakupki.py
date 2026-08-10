"""Уровень A. ЕИС Госзакупки (zakupki.gov.ru): карточки организаций.

Карточки поставщиков/заказчиков в ЕИС часто содержат прямые e-mail и телефоны
контактных лиц — один из самых результативных открытых источников.

Работаем через публичный поиск организаций ЕИС с соблюдением robots.txt:
если робот-политика запрещает путь, источник помечается недоступным и
пропускается (никаких обходов, см. ТЗ п. 5).
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from connectors.base import BaseConnector, register_connector
from core.models import Company, ConnectorResult, Contact, ContactType, SourceLevel
from utils.http import FetchError
from validators.email import extract_emails
from validators.phone import extract_phones

_BASE = "https://zakupki.gov.ru"
_SEARCH_URL = (
    _BASE + "/epz/organization/extendedsearch/results.html"
)
_CARD_LINK_RE = re.compile(r"/epz/organization/view/info\.html\?[^\"']*organizationId=\d+")


@register_connector
class ZakupkiConnector(BaseConnector):
    """Поиск организации в ЕИС и разбор её карточки."""

    name = "zakupki"
    title = "ЕИС Госзакупки"
    level = SourceLevel.A
    default_priority = 20

    def can_run(self, company: Company) -> bool:
        return bool(company.inn)

    async def fetch(self, company: Company) -> ConnectorResult:
        assert company.inn is not None
        search = await self.http.fetch(
            _SEARCH_URL,
            params={
                "searchString": company.inn,
                "morphology": "on",
                "pageNumber": "1",
                "sortDirection": "false",
                "recordsPerPage": "_10",
                "sortBy": "UPDATE_DATE",
            },
            check_robots=True,
            use_cache=True,
        )
        if search.status in (403, 451):
            return ConnectorResult.failed(
                f"ЕИС отвечает HTTP {search.status} — источник закрыт, пропускаем")
        if not search.ok:
            raise FetchError(f"поиск ЕИС вернул HTTP {search.status}",
                             url=search.url, status=search.status,
                             retry_later=search.status >= 500)

        card_url = self._first_card_url(search.text)
        if not card_url:
            return ConnectorResult(ok=True, error="организация не найдена в ЕИС")

        card = await self.http.fetch(card_url, check_robots=True, use_cache=True)
        if not card.ok:
            return ConnectorResult(ok=True,
                                   error=f"карточка ЕИС вернула HTTP {card.status}")

        return self._parse_card(company, card.text, card_url)

    # ------------------------------------------------------------------ #

    def _first_card_url(self, html: str) -> Optional[str]:
        match = _CARD_LINK_RE.search(html)
        if not match:
            return None
        return urljoin(_BASE, match.group(0).replace("&amp;", "&"))

    def _parse_card(self, company: Company, html: str, card_url: str) -> ConnectorResult:
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)

        contacts: list[Contact] = []
        for email in extract_emails(text):
            contacts.append(Contact(
                type=ContactType.EMAIL, value=email, raw=email,
                source=self.name, source_url=card_url, level=self.level,
                extra={"context": "карточка организации ЕИС"},
            ))
        for phone in extract_phones(text):
            contacts.append(Contact(
                type=ContactType.PHONE, value=phone, raw=phone,
                source=self.name, source_url=card_url, level=self.level,
                extra={"context": "карточка организации ЕИС"},
            ))

        updates: dict[str, str] = {}
        # Контактное лицо из карточки — деловой контакт организации
        person = self._labeled_value(soup, ("Контактное лицо",))
        if person:
            updates["director_name"] = person.title()
            updates["director_position"] = "Контактное лицо (ЕИС)"
        site = self._labeled_value(soup, ("Адрес сайта", "Сайт", "Официальный сайт"))
        if site and "." in site and "zakupki.gov.ru" not in site:
            url = site if site.startswith("http") else "https://" + site.strip("/ ")
            updates["website_candidate"] = url
            contacts.append(Contact(
                type=ContactType.WEBSITE, value=url, raw=site,
                source=self.name, source_url=card_url, level=self.level,
            ))

        if not contacts and not updates:
            return ConnectorResult(ok=True, error="в карточке ЕИС нет контактов")
        return ConnectorResult(contacts=contacts, company_updates=updates,
                               source_urls=[card_url])

    @staticmethod
    def _labeled_value(soup: BeautifulSoup, labels: tuple[str, ...]) -> Optional[str]:
        """Найти значение по подписи в таблицах/списках карточки ЕИС."""
        for label in labels:
            node = soup.find(string=re.compile(re.escape(label), re.IGNORECASE))
            if node is None:
                continue
            parent = node.find_parent(["td", "th", "dt", "div", "span", "li"])
            if parent is None:
                continue
            sibling = parent.find_next_sibling(["td", "dd", "div", "span"])
            if sibling is not None:
                value = sibling.get_text(" ", strip=True)
                if value:
                    return value
        return None
