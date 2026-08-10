"""Уровень B. Сайт компании: контактные страницы, футер, микроразметка.

Обходит главную и типовые контактные страницы (/contacts, /kontakty, /about,
/o-kompanii и найденные в меню ссылки), извлекает:
- e-mail (включая обфусцированные «at»/«собака»; адреса-картинки пропускаются);
- телефоны (tel:-ссылки и текст);
- мессенджеры и соцсети (t.me, wa.me, vk.com, ok.ru, rutube, dzen, youtube);
- JSON-LD / микроразметку schema.org Organization;
- реквизиты из футера (ИНН — для верификации домена).

Верификация домена: сайт считается подтверждённым, только если на страницах
найден ИНН компании или совпало название (ТЗ, раздел 3D). Иначе сайт остаётся
«предположительным», а контакты с него штрафуются в скоринге.

Функции разбора HTML — чистые (без сети), на них написаны pytest-тесты.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from connectors.base import BaseConnector, register_connector
from core.models import Company, ConnectorResult, Contact, ContactType, SourceLevel
from utils.http import FetchError, RobotsDisallowed
from utils.obfuscation import deobfuscate_text
from validators.email import extract_emails
from validators.phone import extract_phones, normalize_phone

# Типовые пути контактных страниц (ТЗ, раздел 3B)
CONTACT_PATHS = [
    "/contacts", "/contact", "/kontakty", "/kontakti", "/kontakt",
    "/about", "/about-us", "/o-kompanii", "/o-nas", "/company",
    "/contacts.html", "/kontakty.html", "/about.html",
    "/rekvizity", "/requisites",
]

# Ключевые слова для поиска контактных ссылок в меню/футере
_LINK_HINTS = re.compile(
    r"контакт|о компании|о нас|реквизит|связ|about|contact", re.IGNORECASE
)

_SOCIAL_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("telegram", re.compile(r"(?:t\.me|telegram\.me)/([\w@+\-]+)", re.I), "messenger"),
    ("whatsapp", re.compile(r"(?:wa\.me|api\.whatsapp\.com/send)[/?]([\w?=+%\-]*)", re.I), "messenger"),
    ("viber", re.compile(r"viber://[\w?=+%./\-]+", re.I), "messenger"),
    ("vk", re.compile(r"vk\.com/(?!share|away|images|video|wall)([\w.\-]+)", re.I), "social"),
    ("ok", re.compile(r"ok\.ru/(?!dk\?)(group/[\w\-]+|profile/\d+|[\w.\-]+)", re.I), "social"),
    ("youtube", re.compile(r"youtube\.com/(@[\w.\-]+|channel/[\w\-]+|c/[\w.\-]+|user/[\w.\-]+)", re.I), "social"),
    ("rutube", re.compile(r"rutube\.ru/(channel/\d+|u/[\w\-]+)", re.I), "social"),
    ("dzen", re.compile(r"dzen\.ru/([\w\-]+)", re.I), "social"),
]

_INN_LABELED_RE = re.compile(r"инн\s*[:№]?\s*(\d{10,12})", re.IGNORECASE)


@dataclass
class PageContacts:
    """Контакты, извлечённые из одной HTML-страницы (чистый разбор)."""

    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    socials: list[tuple[str, str, str]] = field(default_factory=list)  # (сеть, url, тип)
    inns_found: list[str] = field(default_factory=list)
    org_names: list[str] = field(default_factory=list)   # из JSON-LD/заголовков
    contact_links: list[str] = field(default_factory=list)


def parse_contact_page(html: str, base_url: str = "") -> PageContacts:
    """Разобрать HTML: почты, телефоны, соцсети, ИНН, ссылки на контакты."""
    result = PageContacts()
    soup = BeautifulSoup(html or "", "lxml")

    for tag in soup(["script", "style", "noscript"]):
        if tag.name == "script" and tag.get("type") == "application/ld+json":
            continue
        tag.extract() if tag.name != "script" else None

    # --- ссылки: mailto, tel, соцсети, контактные страницы ---------------
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        href_l = href.lower()
        if href_l.startswith("mailto:"):
            addr = href[7:].split("?")[0].strip()
            for email in extract_emails(addr):
                if email not in result.emails:
                    result.emails.append(email)
        elif href_l.startswith("tel:"):
            phone = normalize_phone(href[4:])
            if phone and phone not in result.phones:
                result.phones.append(phone)
        else:
            for network, pattern, kind in _SOCIAL_PATTERNS:
                if pattern.search(href):
                    absolute = urljoin(base_url, href) if base_url else href
                    entry = (network, absolute.split("?utm")[0], kind)
                    if entry not in result.socials:
                        result.socials.append(entry)
                    break
            else:
                link_text = a.get_text(" ", strip=True)
                if _LINK_HINTS.search(href) or _LINK_HINTS.search(link_text or ""):
                    absolute = urljoin(base_url, href) if base_url else href
                    if absolute not in result.contact_links:
                        result.contact_links.append(absolute)

    # --- JSON-LD schema.org Organization ---------------------------------
    for script in soup.find_all("script", type="application/ld+json"):
        payload = script.string or script.get_text()
        if not payload:
            continue
        try:
            data = json.loads(payload)
        except (ValueError, TypeError):
            continue
        for org in _iter_organizations(data):
            _merge_jsonld_org(org, result)

    # --- видимый текст: почты (с деобфускацией), телефоны, ИНН ------------
    text = soup.get_text(" ", strip=True)
    for email in extract_emails(text):
        if email not in result.emails:
            result.emails.append(email)
    for phone in extract_phones(text):
        if phone not in result.phones:
            result.phones.append(phone)
    for m in _INN_LABELED_RE.finditer(deobfuscate_text(text)):
        inn = m.group(1)
        if inn not in result.inns_found:
            result.inns_found.append(inn)

    title = soup.find("title")
    if title and title.get_text(strip=True):
        result.org_names.append(title.get_text(strip=True))
    return result


def _iter_organizations(data: object) -> list[dict]:
    """Достать все объекты Organization/LocalBusiness из JSON-LD."""
    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            node_type = node.get("@type")
            types = node_type if isinstance(node_type, list) else [node_type]
            if any(isinstance(t, str) and t.lower() in
                   ("organization", "localbusiness", "corporation", "store",
                    "professionalservice", "generalcontractor", "homeandconstructionbusiness")
                   for t in types if t):
                found.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return found


def _merge_jsonld_org(org: dict, result: PageContacts) -> None:
    email = org.get("email")
    if isinstance(email, str):
        for e in extract_emails(email):
            if e not in result.emails:
                result.emails.append(e)
    phone_value = org.get("telephone") or org.get("phone")
    phones = phone_value if isinstance(phone_value, list) else [phone_value]
    for p in phones:
        if isinstance(p, str):
            normalized = normalize_phone(p)
            if normalized and normalized not in result.phones:
                result.phones.append(normalized)
    name = org.get("name")
    if isinstance(name, str) and name.strip():
        result.org_names.append(name.strip())
    same_as = org.get("sameAs")
    links = same_as if isinstance(same_as, list) else [same_as]
    for link in links:
        if not isinstance(link, str):
            continue
        for network, pattern, kind in _SOCIAL_PATTERNS:
            if pattern.search(link):
                entry = (network, link, kind)
                if entry not in result.socials:
                    result.socials.append(entry)
                break
    tax_id = org.get("taxID") or org.get("vatID")
    if isinstance(tax_id, str):
        digits = re.sub(r"\D", "", tax_id)
        if len(digits) in (10, 12) and digits not in result.inns_found:
            result.inns_found.append(digits)


@register_connector
class WebsiteConnector(BaseConnector):
    """Обход сайта компании (подтверждённого или предположительного)."""

    name = "website"
    title = "Сайт компании"
    level = SourceLevel.B
    default_priority = 40

    def can_run(self, company: Company) -> bool:
        return bool(company.any_website)

    async def fetch(self, company: Company) -> ConnectorResult:
        site = company.any_website
        assert site is not None
        if not site.lower().startswith(("http://", "https://")):
            site = "https://" + site

        max_pages = int(self.config.source_cfg(self.name).get("max_pages", 8))
        base_parts = urlsplit(site)
        base_host = base_parts.netloc.lower()

        queue: list[str] = [site]
        for path in CONTACT_PATHS:
            queue.append(urljoin(site, path))

        visited: set[str] = set()
        merged = PageContacts()
        pages_fetched = 0
        fetched_urls: list[str] = []
        first_error: Optional[str] = None

        while queue and pages_fetched < max_pages:
            url = queue.pop(0)
            norm = url.rstrip("/")
            if norm in visited:
                continue
            visited.add(norm)
            if urlsplit(url).netloc.lower().removeprefix("www.") != base_host.removeprefix("www."):
                continue
            try:
                resp = await self.http.fetch(url, check_robots=True, use_cache=True)
            except RobotsDisallowed:
                self.log.debug("[%s] robots.txt запрещает %s", company.key, url)
                continue
            except FetchError as exc:
                if first_error is None:
                    first_error = str(exc)
                continue
            if resp.status == 404 or not resp.ok:
                continue
            if "text/html" not in (resp.content_type or "text/html"):
                continue
            pages_fetched += 1
            fetched_urls.append(resp.url)
            page = parse_contact_page(resp.text, base_url=resp.url)
            self._merge_pages(merged, page)
            # найденные контактные ссылки добавляем в очередь обхода
            for link in page.contact_links:
                if link.rstrip("/") not in visited and len(queue) < max_pages * 2:
                    queue.append(link)

        if pages_fetched == 0:
            error = first_error or "сайт не отвечает"
            return ConnectorResult.failed(f"сайт {site}: {error}", retry_later=False)

        # --- верификация домена по ИНН/названию ---------------------------
        verified = False
        if company.inn and company.inn in merged.inns_found:
            verified = True
        elif not company.inn and merged.inns_found:
            verified = False
        elif merged.org_names:
            target = self.company_query_name(company) or ""
            verified = any(self.names_similar(target, candidate, threshold=0.55)
                           for candidate in merged.org_names)

        updates: dict[str, object] = {}
        if verified:
            updates["website"] = site
            updates["website_verified"] = True
        elif not company.website:
            updates["website_candidate"] = site

        main_url = fetched_urls[0]
        contacts = self._contacts_from_pages(merged, main_url, verified)
        return ConnectorResult(contacts=contacts, company_updates=updates,
                               source_urls=fetched_urls)

    # ------------------------------------------------------------------ #

    @staticmethod
    def _merge_pages(target: PageContacts, page: PageContacts) -> None:
        for email in page.emails:
            if email not in target.emails:
                target.emails.append(email)
        for phone in page.phones:
            if phone not in target.phones:
                target.phones.append(phone)
        for social in page.socials:
            if social not in target.socials:
                target.socials.append(social)
        for inn in page.inns_found:
            if inn not in target.inns_found:
                target.inns_found.append(inn)
        for name in page.org_names:
            if name not in target.org_names:
                target.org_names.append(name)

    def _contacts_from_pages(self, merged: PageContacts, source_url: str,
                             verified: bool) -> list[Contact]:
        contacts: list[Contact] = []
        extra = {"site_verified_by_inn": verified}
        for email in merged.emails:
            contacts.append(Contact(
                type=ContactType.EMAIL, value=email, raw=email,
                source=self.name, source_url=source_url, level=self.level,
                extra=dict(extra),
            ))
        for phone in merged.phones:
            contacts.append(Contact(
                type=ContactType.PHONE, value=phone, raw=phone,
                source=self.name, source_url=source_url, level=self.level,
                extra=dict(extra),
            ))
        for network, url, kind in merged.socials:
            contacts.append(Contact(
                type=ContactType.MESSENGER if kind == "messenger" else ContactType.SOCIAL,
                value=url, raw=url, source=self.name, source_url=source_url,
                level=self.level, extra={"network": network, **extra},
            ))
        return contacts
