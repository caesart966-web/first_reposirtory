"""Источник №2 — официальный сайт компании.

Часто телефона нет ни в ЕГРЮЛ, ни у агрегаторов, но есть на сайте самой
фирмы. Логика: поиском находим домен, отсеиваем агрегаторы и соцсети,
заходим на главную и на типовые страницы контактов, снимаем телефоны.

ИНН на сайте подтверждается, если он указан в подвале/реквизитах. Если
ИНН на сайте не написан, но домен явно принадлежит компании (совпало имя),
контакты помечаются как «средняя достоверность» — их проще проверить руками.
"""
from __future__ import annotations

import re

from ..extract import (
    extract_emails,
    extract_phones,
    is_aggregator,
    page_mentions_inn,
)
from ..http import Fetcher
from ..models import Found
from ..search import domain_of, web_search

# Типовые пути к контактам — пробуем несколько, берём что откроется.
_CONTACT_PATHS = [
    "", "/contacts", "/contacts/", "/kontakty", "/kontakty/", "/contact",
    "/kontakti", "/o-kompanii/kontakty", "/about/contacts", "/company/contacts",
]

# Ключевые слова названия, которые НЕ помогают отличить компанию (шум).
_STOP = {
    "ооо", "оао", "зао", "ао", "пао", "нпо", "нао", "ип", "гк", "ск", "тк",
    "спб", "санкт-петербург", "россия", "компания", "фирма", "групп", "group",
}


def _name_tokens(name: str) -> list[str]:
    """Значимые слова названия для проверки принадлежности домена/страницы."""
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}", name.lower())
    return [w for w in words if w not in _STOP]


def _looks_like_company(url: str, name: str) -> bool:
    """Грубая эвристика: домен или его имя похожи на название компании."""
    dom = domain_of(url)
    if not dom or is_aggregator(dom):
        return False
    # госреестры, справочники, файлопомойки, соцсети — не сайт компании
    if dom.endswith((".gov.ru", ".gosuslugi.ru")):
        return False
    return True


def company_site(company, fetcher: Fetcher, cfg) -> list[Found]:
    query = f'{company.name} Санкт-Петербург официальный сайт контакты'
    candidates = web_search(fetcher, query, limit=10)

    # Оставляем только правдоподобные домены компаний, не агрегаторы.
    domains: list[str] = []
    for url in candidates:
        if _looks_like_company(url, company.name):
            dom = domain_of(url)
            if dom and dom not in domains:
                domains.append(dom)
        if len(domains) >= cfg.max_sites:
            break

    tokens = _name_tokens(company.name)
    out: list[Found] = []

    for dom in domains:
        best: Found | None = None
        for path in _CONTACT_PATHS:
            url = f"https://{dom}{path}"
            html = fetcher.get(url)
            if not html:
                continue

            phones = extract_phones(html)
            emails = extract_emails(html)
            if not phones and not emails:
                continue

            inn_ok = page_mentions_inn(html, company.inn)
            # Без ИНН на странице — доверяем только если имя реально встречается.
            name_ok = any(tok in html.lower() for tok in tokens) if tokens else False
            if not inn_ok and not name_ok:
                continue

            found = Found(
                source="сайт компании",
                url=url,
                inn_confirmed=inn_ok,
                phones=phones,
                emails=emails,
                site=f"https://{dom}",
                note="" if inn_ok else "ИНН на сайте не указан — проверить вручную",
            )
            # Приоритет странице, где подтверждён ИНН.
            if best is None or (found.inn_confirmed and not best.inn_confirmed):
                best = found
            if found.inn_confirmed:
                break

        if best:
            out.append(best)
        if any(f.inn_confirmed and f.phones for f in out):
            break

    return out
