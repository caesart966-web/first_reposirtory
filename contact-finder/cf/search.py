"""Поиск по интернету: DuckDuckGo HTML (без ключей) и опционально Яндекс XML.

Нужен, чтобы найти сайт компании и страницы-карточки, если прямые URL
агрегаторов недоступны. DuckDuckGo отдаёт результаты обычным HTML —
парсим ссылки регулярками, без внешних зависимостей.
"""
from __future__ import annotations

import html as html_mod
import re
import urllib.parse

from .http import Fetcher

_DDG_HTML = "https://html.duckduckgo.com/html/?q="
_DDG_LINK = re.compile(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"', re.I)
_DDG_REDIR = re.compile(r"uddg=([^&]+)")


def _clean_ddg(href: str) -> str:
    """DuckDuckGo заворачивает ссылки в редирект — достаём настоящий URL."""
    match = _DDG_REDIR.search(href)
    if match:
        return urllib.parse.unquote(match.group(1))
    return href


def web_search(fetcher: Fetcher, query: str, limit: int = 10) -> list[str]:
    """Список URL из выдачи. Пустой список — если поиск недоступен."""
    url = _DDG_HTML + urllib.parse.quote(query)
    page = fetcher.get(url)
    if not page:
        return []
    out: list[str] = []
    for href in _DDG_LINK.findall(page):
        real = html_mod.unescape(_clean_ddg(href))
        if real.startswith("http") and real not in out:
            out.append(real)
        if len(out) >= limit:
            break
    return out


def yandex_xml_search(
    fetcher: Fetcher, query: str, user: str, key: str, limit: int = 10
) -> list[str]:
    """Яндекс XML (нужны user+key из Яндекс.Вебмастера). Точнее по РФ-компаниям."""
    base = "https://yandex.ru/search/xml"
    params = urllib.parse.urlencode(
        {"user": user, "key": key, "query": query, "l10n": "ru", "groupby": f"mode=flat.groups-on-page={limit}"}
    )
    page = fetcher.get(f"{base}?{params}")
    if not page:
        return []
    return [html_mod.unescape(u) for u in re.findall(r"<url>([^<]+)</url>", page)][:limit]


def domain_of(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().lstrip("www.")
    except Exception:  # noqa: BLE001
        return ""
