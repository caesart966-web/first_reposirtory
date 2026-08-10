"""Источники-API (высший приоритет) — Checko и Datanewton.

Платные/условно-бесплатные API отдают контакты структурно и уже привязанными
к ИНН, поэтому это самый надёжный и самый дешёвый по числу запросов путь.

Устойчивость к схеме. Точный набор полей у API может меняться, а проверить
живой ответ из офлайна нельзя, поэтому разбор двухступенчатый:
  1) пробуем документированные пути (data.Контакты.Тел и т.п.);
  2) если там пусто — рекурсивно обходим весь JSON и собираем всё, что
     похоже на телефон/почту/сайт по именам ключей и по виду значения.
Так источник переживёт переименование полей.

ИНН считается подтверждённым, если в ответе есть поле ИНН и оно совпало с
запрошенным. Это и есть гарантия, что не подсунули однофамильца.
"""
from __future__ import annotations

import json
import re
import urllib.parse

from ..cache import shared as shared_cache
from ..extract import normalize_phone
from ..http import Fetcher
from ..models import Found

# --- имена ключей, в которых у API лежат контакты -----------------------------
_PHONE_KEY = re.compile(r"(тел|phone|contact_phone)", re.I)
_EMAIL_KEY = re.compile(r"(почт|mail|email)", re.I)
_SITE_KEY = re.compile(r"(сайт|site|website|url|домен|domain)", re.I)
_INN_KEY = re.compile(r"^инн$|_inn$|^inn$", re.I)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_URL_RE = re.compile(r"^(https?://)?([a-z0-9\-]+\.)+[a-z]{2,}(/.*)?$", re.I)


def _iter_nodes(node, key: str = ""):
    """Рекурсивный обход JSON: отдаёт пары (имя_ключа, значение)."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _iter_nodes(v, str(k))
    elif isinstance(node, list):
        for item in node:
            yield from _iter_nodes(item, key)
    else:
        yield key, node


def _collect(payload: dict) -> tuple[list[str], list[str], str, str]:
    """Собирает (телефоны, почты, сайт, инн) из любого по форме JSON."""
    phones: list[str] = []
    emails: list[str] = []
    site = ""
    inn = ""

    for key, value in _iter_nodes(payload):
        if value is None or isinstance(value, (dict, list, bool)):
            continue
        text = str(value).strip()
        if not text:
            continue

        if _INN_KEY.search(key) and text.isdigit() and len(text) in (10, 12):
            inn = inn or text
            continue

        if _PHONE_KEY.search(key):
            phone = normalize_phone(text)
            if phone and phone not in phones:
                phones.append(phone)
            continue

        if _EMAIL_KEY.search(key) and _EMAIL_RE.match(text):
            low = text.lower()
            if low not in emails:
                emails.append(low)
            continue

        if _SITE_KEY.search(key) and _URL_RE.match(text) and "@" not in text:
            site = site or text
            continue

        # Значение похоже на почту/телефон, даже если ключ назван иначе.
        if _EMAIL_RE.match(text) and text.lower() not in emails:
            emails.append(text.lower())

    return phones, emails, site, inn


def _request(fetcher: Fetcher, url: str, cache_key: str, use_cache: bool) -> dict | None:
    """Запрос с кэшированием. Возвращает разобранный JSON либо None."""
    cache = shared_cache()
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            try:
                return json.loads(cached)
            except Exception:  # noqa: BLE001
                pass

    raw = fetcher.get(url)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001
        return None

    cache.put(cache_key, raw)
    return payload


def _meta_problem(payload: dict) -> str:
    """Достаёт человекочитаемую ошибку из meta, если запрос не удался."""
    meta = payload.get("meta") or {}
    status = str(meta.get("status", "")).lower()
    if status and status not in ("ok", "200", "success"):
        return str(meta.get("message") or meta.get("status") or "ошибка API")
    return ""


def checko_api(company, fetcher: Fetcher, cfg) -> list[Found]:
    """Checko API: /v2/company для ЮЛ, /v2/entrepreneur для ИП."""
    if not cfg.checko_key:
        return []

    inn = company.inn
    # 12 знаков — ИП/физлицо, 10 — юрлицо. Если не угадали, пробуем второй путь.
    endpoints = ["entrepreneur", "company"] if len(inn) == 12 else ["company", "entrepreneur"]

    for endpoint in endpoints:
        params = urllib.parse.urlencode({"key": cfg.checko_key, "inn": inn})
        url = f"https://api.checko.ru/v2/{endpoint}?{params}"
        # В ключ кэша не кладём API-ключ — только источник, метод и ИНН.
        payload = _request(fetcher, url, f"checko:{endpoint}:{inn}", not cfg.no_cache)
        if not payload:
            continue

        problem = _meta_problem(payload)
        if problem:
            if cfg.verbose:
                print(f"    ! Checko ({endpoint}): {problem}")
            # Неверный ключ/исчерпан лимит — второй endpoint не поможет.
            if re.search(r"ключ|лимит|limit|key|баланс|balance", problem, re.I):
                return []
            continue

        data = payload.get("data") or payload
        if not isinstance(data, dict) or not data:
            continue

        phones, emails, site, got_inn = _collect(data)
        if not (phones or emails or site):
            continue

        return [
            Found(
                source="Checko API",
                url=f"api.checko.ru/v2/{endpoint} (ИНН {inn})",
                inn_confirmed=(got_inn == inn),
                phones=phones,
                emails=emails,
                site=site,
                note="" if got_inn == inn else "API не вернул ИНН — сверить вручную",
            )
        ]

    return []


def datanewton_api(company, fetcher: Fetcher, cfg) -> list[Found]:
    """Datanewton API — запасной структурный источник, схожий по формату."""
    if not cfg.datanewton_key:
        return []

    params = urllib.parse.urlencode(
        {"key": cfg.datanewton_key, "inn": company.inn, "filters": "ADDRESS_BLOCK,CONTACT_BLOCK"}
    )
    url = f"https://api.datanewton.ru/v1/counterparty?{params}"
    payload = _request(fetcher, url, f"datanewton:{company.inn}", not cfg.no_cache)
    if not payload:
        return []
    if _meta_problem(payload):
        if cfg.verbose:
            print(f"    ! Datanewton: {_meta_problem(payload)}")
        return []

    phones, emails, site, got_inn = _collect(payload)
    if not (phones or emails or site):
        return []

    return [
        Found(
            source="Datanewton API",
            url=f"api.datanewton.ru (ИНН {company.inn})",
            inn_confirmed=(got_inn == company.inn),
            phones=phones,
            emails=emails,
            site=site,
        )
    ]
