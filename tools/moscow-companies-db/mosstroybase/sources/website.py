"""Сбор контактов с сайта компании: главная страница + типовые страницы контактов.

Работает вежливо: небольшое число страниц на сайт, пауза между запросами,
честный User-Agent. Ошибки сети и недоступные сайты просто пропускаются.
"""

from __future__ import annotations

import re
import time
from html import unescape
from urllib.parse import urljoin, urlparse

import requests

from ..normalize import extract_emails, extract_phones

CONTACT_PATHS = ("", "/contacts", "/kontakty", "/contact", "/kontakti", "/about")

_MAILTO_RE = re.compile(r"mailto:([^\"'?>\s]+)", re.I)
_TEL_RE = re.compile(r"tel:([^\"'>\s]+)", re.I)
_CONTACT_LINK_RE = re.compile(
    r"href=[\"']([^\"']*(?:contact|kontakt|контакт)[^\"']*)[\"']", re.I
)


def normalize_url(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    if not raw.startswith(("http://", "https://")):
        raw = "http://" + raw
    parsed = urlparse(raw)
    if not parsed.netloc or "." not in parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def harvest(
    website: str,
    session: requests.Session,
    delay: float = 1.0,
    timeout: int = 15,
    max_pages: int = 4,
) -> dict:
    """Возвращает {'emails': [...], 'phones': [...]} со страниц сайта."""
    base = normalize_url(website)
    result: dict = {"emails": [], "phones": []}
    if not base:
        return result

    urls = [base + path for path in CONTACT_PATHS]
    seen: set[str] = set()
    pages = 0
    while urls and pages < max_pages:
        url = urls.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            resp = session.get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code != 200:
                continue
            html = resp.text
        except requests.RequestException:
            continue
        pages += 1

        _collect(html, result)
        # Со страницы главной подхватываем явные ссылки на «Контакты»
        for match in _CONTACT_LINK_RE.findall(html)[:3]:
            link = urljoin(url + "/", match)
            if link.startswith(base) and link not in seen:
                urls.insert(0, link)
        time.sleep(delay)
    return result


def _collect(html: str, result: dict) -> None:
    text = unescape(html)
    for raw in _MAILTO_RE.findall(text):
        for email in extract_emails(raw):
            if email not in result["emails"]:
                result["emails"].append(email)
    for raw in _TEL_RE.findall(text):
        for phone in extract_phones(raw):
            if phone not in result["phones"]:
                result["phones"].append(phone)
    for email in extract_emails(text):
        if email not in result["emails"]:
            result["emails"].append(email)
    for phone in extract_phones(text):
        if phone not in result["phones"]:
            result["phones"].append(phone)
