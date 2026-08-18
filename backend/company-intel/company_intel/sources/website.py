"""Сайт компании: обход контактных страниц и разбор реквизитов.

Самый ценный источник: на собственном сайте компания публикует контакты
добровольно и держит их в актуальном состоянии. Обход ограничен несколькими
страницами — берём главную и всё, что похоже на «Контакты» и «Реквизиты».
"""
from __future__ import annotations

import asyncio
import heapq
import re
from urllib.parse import urlsplit

from ..extract import parse_page
from ..models import Finding
from ..normalize import normalize_domain, normalize_company_name
from .base import Context, Source

# Пути, которые почти всегда содержат контакты, — пробуем напрямую.
COMMON_PATHS = (
    "/contacts", "/kontakty", "/contact", "/rekvizity", "/requisites",
    "/about", "/o-kompanii", "/about-us", "/company", "/o-nas", "/impressum",
)
# Слова в ссылке или её тексте, повышающие приоритет страницы.
LINK_HINTS = (
    "контакт", "contact", "kontakt", "связ", "реквизит", "requisit", "rekvizit",
    "о компании", "о нас", "about", "company", "impressum", "команда", "team",
    "руковод", "офис", "office", "адрес", "address", "франшиз", "юридическ",
)
PAGE_WEIGHT = {"contacts": 0.78, "requisites": 0.8, "about": 0.68, "home": 0.7, "other": 0.55}


def _canonical(url: str) -> str:
    """URL без якоря и хвостового слэша — чтобы /contacts и /contacts/ не считались разными."""
    parts = urlsplit(url)
    path = parts.path.rstrip("/") or "/"
    return f"{parts.scheme}://{parts.netloc}{path}?{parts.query}"


def _page_kind(url: str) -> str:
    path = urlsplit(url).path.lower().strip("/")
    if not path:
        return "home"
    if any(w in path for w in ("rekvizit", "requisit")):
        return "requisites"
    if any(w in path for w in ("contact", "kontakt", "svyaz")):
        return "contacts"
    if any(w in path for w in ("about", "company", "o-kompanii", "o-nas", "team")):
        return "about"
    return "other"


class WebsiteSource(Source):
    name = "website"
    title = "Официальный сайт компании"
    reliability = 0.75
    legal_note = "Соблюдается robots.txt и пауза между запросами."

    def input_signature(self, ctx: Context) -> str:
        return "|".join(ctx.domains())

    async def run(self, ctx: Context) -> list[Finding]:
        domains = ctx.domains()[:2]
        if not domains:
            return []
        results = await asyncio.gather(*(self._crawl_site(ctx, d) for d in domains))
        return [f for chunk in results for f in chunk]

    async def _crawl_site(self, ctx: Context, domain: str) -> list[Finding]:
        start = await self._resolve_start(ctx, domain)
        if not start:
            return []
        home_url, home_html = start
        parts = urlsplit(home_url)
        base = f"{parts.scheme}://{parts.netloc}"
        budget = max(1, ctx.config.max_pages_per_site)

        visited = {_canonical(home_url)}
        queue: list[tuple[int, int, str]] = []   # (-приоритет, счётчик, url)
        counter = 0

        def enqueue(links: list[str], bonus: int = 0) -> None:
            nonlocal counter
            for score, url in self._score_links(links):
                if _canonical(url) in visited:
                    continue
                counter += 1
                heapq.heappush(queue, (-(score + bonus), counter, url))

        home_page = parse_page(home_html, home_url, ctx.config.country)
        pages = [home_page]
        enqueue(home_page.links)
        enqueue([base + path for path in COMMON_PATHS], bonus=2)

        while queue and len(pages) < budget:
            _, _, url = heapq.heappop(queue)
            key = _canonical(url)
            if key in visited:
                continue
            visited.add(key)
            resp = await ctx.fetcher.get(url)
            if not resp or not resp.ok or not resp.text:
                continue
            visited.add(_canonical(resp.url))
            page = parse_page(resp.text, resp.url, ctx.config.country)
            pages.append(page)
            # Ссылки со второго уровня: «Реквизиты» часто есть только в подвале
            # внутренних страниц, а не на главной.
            enqueue(page.links)

        findings: list[Finding] = []
        for page in pages:
            findings.extend(self._page_findings(page, ctx))
        real_domain = normalize_domain(home_url)
        if real_domain:
            findings.append(self.finding(
                "domain", real_domain, url=home_url, note="сайт отвечает", confidence=0.85,
            ))
        return findings

    async def _resolve_start(self, ctx: Context, domain: str):
        for scheme in ("https", "http"):
            url = f"{scheme}://{domain}/"
            resp = await ctx.fetcher.get(url)
            if resp and resp.ok and resp.text:
                return (str(resp.url), resp.text)
        return None

    def _score_links(self, links: list[str]) -> list[tuple[int, str]]:
        """Оценивает ссылки: чем ближе к контактам и мельче вложенность, тем выше."""
        scored: list[tuple[int, str]] = []
        seen: set[str] = set()
        for link in links:
            low = link.lower()
            if re.search(r"\.(pdf|jpe?g|png|gif|zip|rar|docx?|xlsx?)$", low):
                continue
            if low in seen:
                continue
            seen.add(low)
            score = sum(3 for hint in LINK_HINTS if hint in low)
            score -= urlsplit(low).path.strip("/").count("/")
            if score > 0:
                scored.append((score, link))
        scored.sort(key=lambda x: -x[0])
        return scored

    def _rank_links(self, links: list[str], domain: str = "") -> list[str]:
        """Совместимый со старым API порядок ссылок (используется в тестах)."""
        return [link for _, link in self._score_links(links)]

    def _page_findings(self, page, ctx: Context) -> list[Finding]:
        url = page.url
        kind = _page_kind(url)
        weight = PAGE_WEIGHT.get(kind, 0.55)
        out: list[Finding] = []

        for email in page.emails:
            out.append(self.finding("email", email, url=url, note=f"страница: {kind}",
                                    confidence=weight))
        for phone, ext, label in page.phones:
            out.append(self.finding("phone", phone, url=url, note=f"страница: {kind}",
                                    confidence=weight, extension=ext, label=label))
        for req_kind, values in page.requisites.items():
            for value in values:
                # Реквизиты с сошедшейся контрольной суммой на своём сайте — почти факт.
                out.append(self.finding(req_kind, value, url=url,
                                        note="контрольная сумма сошлась", confidence=0.88))
        for address in page.addresses:
            out.append(self.finding("address", address, url=url, confidence=weight * 0.9))
        for fio, position in page.persons:
            out.append(self.finding("person", fio, url=url, confidence=weight * 0.85,
                                    position=position))
        for network, link in page.socials:
            out.append(self.finding("social", link, url=url, confidence=0.8, network=network))
        if kind == "home" and page.title:
            name = normalize_company_name(re.split(r"[|—–\-]{1,2}", page.title)[0])
            if name and 2 < len(name) < 120:
                out.append(self.finding("name", name, url=url, note="заголовок главной",
                                        confidence=0.45))
        return out
