"""Поисковая выдача через официальные API (SerpApi, Google CSE, Яндекс XML, Brave).

Поисковик — это «широкая сеть»: он находит компанию там, где её сайт не
упоминает, — в каталогах, отзывах, вакансиях, тендерах, новостях. Работаем
только через API поисковых систем: парсинг HTML-выдачи нарушает их правила
и всё равно ломается на капче.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Callable

from ..extract import classify_social, extract_emails, extract_phones, parse_page
from ..models import Finding
from ..normalize import normalize_domain, registrable_domain
from .base import Context, Source


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


class SearchSource(Source):
    name = "search"
    title = "Поисковая выдача (API)"
    reliability = 0.6
    needs_keys = ()  # проверяем «любой из» в available()
    legal_note = "Используются официальные API поисковых систем, а не скрейпинг выдачи."

    ANY_KEYS = (
        ("SERPAPI_KEY",),
        ("GOOGLE_CSE_KEY", "GOOGLE_CSE_CX"),
        ("YANDEX_XML_USER", "YANDEX_XML_KEY"),
        ("BRAVE_API_KEY",),
    )

    def available(self, config) -> tuple[bool, str]:
        if not config.is_enabled(self.name):
            return False, "отключён настройками"
        if any(config.has(*combo) for combo in self.ANY_KEYS):
            return True, ""
        return False, "нужен ключ одного из: SerpApi, Google CSE, Яндекс XML, Brave"

    def input_signature(self, ctx: Context) -> str:
        return "|".join(sorted(set(self._queries(ctx))))

    def _queries(self, ctx: Context) -> list[str]:
        q = ctx.query
        names = ctx.names()
        out: list[str] = []
        if names:
            name = f'"{names[0]}"'
            out.append(f"{name} контакты телефон email")
            out.append(f"{name} ИНН реквизиты")
            if not ctx.persons():
                out.append(f"{name} генеральный директор")
        for domain in ctx.domains()[:1]:
            out.append(f"{domain} контакты email")
        if q.phone:
            out.append(f'"{q.phone}"')
        if q.email:
            out.append(f'"{q.email}"')
        if q.person and not names:
            out.append(f'"{q.person}" компания контакты')
        if q.city and names:
            out[0] = f"{out[0]} {q.city}"
        return out[:5]

    async def run(self, ctx: Context) -> list[Finding]:
        adapter = self._pick_adapter(ctx)
        if adapter is None:
            return []
        engine, fetch = adapter
        per_query = max(3, ctx.config.max_search_results // max(1, len(self._queries(ctx))))
        results = await asyncio.gather(
            *(fetch(ctx, query, per_query) for query in self._queries(ctx))
        )
        hits: list[SearchHit] = []
        seen_urls: set[str] = set()
        for chunk in results:
            for hit in chunk:
                if hit.url in seen_urls:
                    continue
                seen_urls.add(hit.url)
                hits.append(hit)

        out: list[Finding] = []
        for hit in hits:
            out.extend(self._from_hit(ctx, hit, engine))
        if ctx.config.fetch_search_results:
            out.extend(await self._fetch_pages(ctx, hits))
        return out

    # -- разбор выдачи ------------------------------------------------------

    def _from_hit(self, ctx: Context, hit: SearchHit, engine: str) -> list[Finding]:
        out: list[Finding] = []
        text = f"{hit.title}\n{hit.snippet}"
        note = f"сниппет {engine}"
        for email in extract_emails(text):
            out.append(self.finding("email", email, url=hit.url, note=note, confidence=0.45))
        for phone, ext, label in extract_phones(text, ctx.config.country):
            out.append(self.finding("phone", phone, url=hit.url, note=note,
                                    confidence=0.4, extension=ext, label=label))
        social = classify_social(hit.url)
        if social:
            out.append(self.finding("social", social[1], url=hit.url, note=note,
                                    confidence=0.6, network=social[0]))
        else:
            out.append(self.finding("url", hit.url, note=f"{note}: {hit.title[:120]}",
                                    confidence=0.5, title=hit.title, snippet=hit.snippet[:300]))
        return out

    async def _fetch_pages(self, ctx: Context, hits: list[SearchHit]) -> list[Finding]:
        own = {registrable_domain(d) for d in ctx.domains()}
        targets: list[SearchHit] = []
        for hit in hits:
            host = normalize_domain(hit.url)
            if not host or classify_social(hit.url):
                continue
            if registrable_domain(host) in own:
                continue  # свой сайт уже обходит website-источник
            targets.append(hit)
            if len(targets) >= 6:
                break
        pages = await asyncio.gather(*(ctx.fetcher.get(hit.url) for hit in targets))
        out: list[Finding] = []
        for hit, resp in zip(targets, pages):
            if not resp or not resp.ok or not resp.text:
                continue
            page = parse_page(resp.text, hit.url, ctx.config.country)
            if not self._page_mentions_company(ctx, page.text):
                continue  # страница о другой компании — не тащим её контакты
            note = "страница из выдачи"
            for email in page.emails:
                out.append(self.finding("email", email, url=hit.url, note=note, confidence=0.45))
            for phone, ext, label in page.phones:
                out.append(self.finding("phone", phone, url=hit.url, note=note,
                                        confidence=0.4, extension=ext, label=label))
            for req_kind, values in page.requisites.items():
                for value in values:
                    out.append(self.finding(req_kind, value, url=hit.url, note=note,
                                            confidence=0.6))
            for address in page.addresses[:3]:
                out.append(self.finding("address", address, url=hit.url, note=note,
                                        confidence=0.4))
            for fio, position in page.persons[:5]:
                out.append(self.finding("person", fio, url=hit.url, note=note,
                                        confidence=0.4, position=position))
            for network, link in page.socials:
                out.append(self.finding("social", link, url=hit.url, note=note,
                                        confidence=0.5, network=network))
        return out

    def _page_mentions_company(self, ctx: Context, text: str) -> bool:
        """Грубая проверка релевантности: на странице есть ИНН, домен или название."""
        low = (text or "").lower()
        inn = ctx.inn()
        if inn and inn in low:
            return True
        for domain in ctx.domains():
            if domain.lower() in low:
                return True
        for name in ctx.names():
            core = re.sub(r'["«»]', "", name).lower()
            core = re.sub(r"\b(ооо|оао|зао|пао|ао|ип)\b", "", core).strip()
            if len(core) >= 4 and core in low:
                return True
        return False

    # -- адаптеры поисковых систем -----------------------------------------

    def _pick_adapter(self, ctx: Context) -> tuple[str, Callable] | None:
        cfg = ctx.config
        if cfg.has("SERPAPI_KEY"):
            return "serpapi", self._serpapi
        if cfg.has("GOOGLE_CSE_KEY", "GOOGLE_CSE_CX"):
            return "google_cse", self._google_cse
        if cfg.has("YANDEX_XML_USER", "YANDEX_XML_KEY"):
            return "yandex_xml", self._yandex_xml
        if cfg.has("BRAVE_API_KEY"):
            return "brave", self._brave
        return None

    async def _serpapi(self, ctx: Context, query: str, count: int) -> list[SearchHit]:
        data = await ctx.fetcher.get_json(
            "https://serpapi.com/search.json",
            params={"q": query, "api_key": ctx.config.key("SERPAPI_KEY"),
                    "engine": "google", "hl": "ru", "num": count},
            check_robots=False,
        )
        if not isinstance(data, dict):
            return []
        return [
            SearchHit(item.get("title", ""), item.get("link", ""), item.get("snippet", ""))
            for item in data.get("organic_results", []) if item.get("link")
        ][:count]

    async def _google_cse(self, ctx: Context, query: str, count: int) -> list[SearchHit]:
        data = await ctx.fetcher.get_json(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": ctx.config.key("GOOGLE_CSE_KEY"),
                    "cx": ctx.config.key("GOOGLE_CSE_CX"),
                    "q": query, "num": min(10, count), "hl": "ru"},
            check_robots=False,
        )
        if not isinstance(data, dict):
            return []
        return [
            SearchHit(item.get("title", ""), item.get("link", ""), item.get("snippet", ""))
            for item in data.get("items", []) if item.get("link")
        ][:count]

    async def _yandex_xml(self, ctx: Context, query: str, count: int) -> list[SearchHit]:
        resp = await ctx.fetcher.get(
            "https://yandex.ru/search/xml",
            params={"user": ctx.config.key("YANDEX_XML_USER"),
                    "key": ctx.config.key("YANDEX_XML_KEY"),
                    "query": query, "l10n": "ru", "groupby": f"attr=d.mode=deep.groups-on-page={count}"},
            check_robots=False,
        )
        if not resp or not resp.ok:
            return []
        return parse_yandex_xml(resp.text)[:count]

    async def _brave(self, ctx: Context, query: str, count: int) -> list[SearchHit]:
        data = await ctx.fetcher.get_json(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": min(20, count)},
            headers={"X-Subscription-Token": ctx.config.key("BRAVE_API_KEY") or "",
                     "Accept": "application/json"},
            check_robots=False,
        )
        if not isinstance(data, dict):
            return []
        results = (data.get("web") or {}).get("results") or []
        return [
            SearchHit(item.get("title", ""), item.get("url", ""), item.get("description", ""))
            for item in results if item.get("url")
        ][:count]


def parse_yandex_xml(xml: str) -> list[SearchHit]:
    """Разбор ответа Яндекс XML (вынесено отдельно ради тестируемости)."""
    import xml.etree.ElementTree as ET

    def text_of(node) -> str:
        return re.sub(r"\s+", " ", "".join(node.itertext())).strip() if node is not None else ""

    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    hits: list[SearchHit] = []
    for doc in root.iter("doc"):
        url = (doc.findtext("url") or "").strip()
        if not url:
            continue
        title = text_of(doc.find("title"))
        passages = doc.find("passages")
        snippet = text_of(passages) or text_of(doc.find("headline"))
        hits.append(SearchHit(title, url, snippet))
    return hits
