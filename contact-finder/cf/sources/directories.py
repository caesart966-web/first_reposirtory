"""Источник №3 — гео-справочники (2ГИС, Яндекс.Карты, Zoon, Yell).

Именно этот приём вручную дал телефоны ПРОФИЛЬ-ДЕКОР и НИДУС: у справочника
карточка привязана к адресу из ЕГРЮЛ, и телефон почти всегда на виду.

2ГИС/Яндекс отдают контент через JS, поэтому «сырой» HTML часто пуст. Но:
  * у 2ГИС есть публичный Catalog API (нужен ключ) — если задан, используем;
  * иначе снимаем что получится из HTML-версий (yell, zoon, orgpage),
    подтверждая принадлежность по совпадению адреса/названия.
"""
from __future__ import annotations

import json
import re
import urllib.parse

from ..extract import extract_emails, extract_phones, page_mentions_inn
from ..http import Fetcher
from ..models import Found
from ..search import web_search

# HTML-справочники, из которых реально что-то парсится без JS.
_HTML_DIR_HINTS = ["yell.ru", "zoon.ru", "orgpage.ru", "spravker.ru", "regtorg.ru"]


def _dgis_catalog(company, fetcher: Fetcher, cfg) -> Found | None:
    """2ГИС Catalog API — точные телефоны, если задан ключ (cfg.dgis_key)."""
    if not cfg.dgis_key:
        return None
    q = urllib.parse.urlencode(
        {"q": f"{company.name}", "key": cfg.dgis_key, "fields": "items.contact_groups", "page_size": 5}
    )
    raw = fetcher.get(f"https://catalog.api.2gis.com/3.0/items?{q}")
    if not raw:
        return None
    try:
        data = json.loads(raw)
        items = data.get("result", {}).get("items", [])
    except Exception:  # noqa: BLE001
        return None

    phones: list[str] = []
    for item in items:
        for group in item.get("contact_groups", []):
            for contact in group.get("contacts", []):
                if contact.get("type") == "phone":
                    from ..extract import normalize_phone
                    ph = normalize_phone(contact.get("value", ""))
                    if ph and ph not in phones:
                        phones.append(ph)
    if not phones:
        return None
    # 2ГИС не отдаёт ИНН — помечаем как требующее ручной сверки по адресу.
    return Found(
        source="2ГИС API",
        url="catalog.api.2gis.com",
        inn_confirmed=False,
        phones=phones,
        note="2ГИС не публикует ИНН — сверить адрес вручную",
    )


def map_directories(company, fetcher: Fetcher, cfg) -> list[Found]:
    out: list[Found] = []

    api = _dgis_catalog(company, fetcher, cfg)
    if api:
        out.append(api)

    # HTML-справочники по названию.
    query = f'{company.name} Санкт-Петербург телефон адрес'
    for url in web_search(fetcher, query, limit=10):
        if not any(hint in url for hint in _HTML_DIR_HINTS):
            continue
        html = fetcher.get(url)
        if not html:
            continue
        phones = extract_phones(html)
        if not phones:
            continue
        out.append(
            Found(
                source="справочник",
                url=url,
                inn_confirmed=page_mentions_inn(html, company.inn),
                phones=phones,
                emails=extract_emails(html),
                note="справочник — если ИНН не подтверждён, сверить адрес",
            )
        )
        break

    return out
