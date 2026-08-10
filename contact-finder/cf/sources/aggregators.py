"""Источник №1 — карточки на сайтах-агрегаторах по прямым URL.

Многие агрегаторы дают карточку по ИНН или ОГРН прямым адресом, без входа
в поисковую форму. Пробуем такие URL, качаем страницу и — ключевое —
принимаем контакты, только если на странице реально есть искомый ИНН.
Так парсер не путает однофамильцев и переживает смену вёрстки.
"""
from __future__ import annotations

from ..extract import (
    extract_emails,
    extract_phones,
    find_ogrn,
    page_mentions_inn,
)
from ..http import Fetcher
from ..models import Found
from ..search import web_search

# Шаблоны прямых карточек. {inn} и {ogrn} подставляются.
# Порядок — по «щедрости» источника на телефоны.
_DIRECT_TEMPLATES = [
    ("list-org", "https://www.list-org.com/search?type=inn&val={inn}"),
    ("audit-it", "https://www.audit-it.ru/contragent/{inn}"),
    ("rusprofile", "https://www.rusprofile.ru/search?query={inn}"),
    ("checko", "https://checko.ru/company/inn/{inn}"),
    ("sbis", "https://sbis.ru/contragents/{inn}/{kpp}"),
    ("ngee", "https://ngee.ru/ooo-{inn}.html"),
]

# Через поиск: находим карточку на агрегаторе, если прямой URL не сработал.
_SEARCH_HINTS = ["rusprofile.ru", "list-org.com", "audit-it.ru", "checko.ru"]


def _harvest(source: str, url: str, html: str, inn: str) -> Found | None:
    """Снять контакты со страницы, если на ней подтверждён ИНН."""
    if not html:
        return None
    confirmed = page_mentions_inn(html, inn)
    phones = extract_phones(html)
    emails = extract_emails(html)
    if not phones and not emails:
        return None
    return Found(
        source=source,
        url=url,
        inn_confirmed=confirmed,
        phones=phones,
        emails=emails,
        ogrn=find_ogrn(html) or "",
    )


def aggregator_cards(company, fetcher: Fetcher, cfg) -> list[Found]:
    from ..extract import default_kpp

    out: list[Found] = []
    kpp = default_kpp(company.inn) or "770101001"

    # 1) Прямые URL-шаблоны.
    for source, template in _DIRECT_TEMPLATES:
        url = template.format(inn=company.inn, ogrn="", kpp=kpp)
        html = fetcher.get(url)
        found = _harvest(source, url, html or "", company.inn)
        if found:
            out.append(found)
            if found.inn_confirmed and found.phones:
                break  # хватит одного надёжного попадания с телефоном

    # 2) Если прямые не дали подтверждённого телефона — ищем карточку поиском.
    if not any(f.inn_confirmed and f.phones for f in out):
        query = f'{company.name} ИНН {company.inn} телефон'
        for url in web_search(fetcher, query, limit=8):
            if not any(hint in url for hint in _SEARCH_HINTS):
                continue
            html = fetcher.get(url)
            found = _harvest("поиск→агрегатор", url, html or "", company.inn)
            if found:
                out.append(found)
                if found.inn_confirmed and found.phones:
                    break

    return out
