"""Checko API — телефоны, e-mail и сайт компании по ИНН.

Нужен бесплатный API-ключ (https://checko.ru/integration/api, лимит
бесплатного тарифа ~100 запросов/сутки). Ключ передаётся через
переменную окружения CHECKO_API_KEY или флаг --key.

Структура ответа может меняться, поэтому контакты извлекаются
рекурсивным обходом по «смысловым» ключам.
"""

from __future__ import annotations

import requests

from ..config import CHECKO_COMPANY_URL
from ..normalize import extract_emails, extract_phones
from .egrul import deep_find, walk


def fetch(inn: str, api_key: str, session: requests.Session, timeout: int = 30) -> dict | None:
    resp = session.get(
        CHECKO_COMPANY_URL, params={"key": api_key, "inn": inn}, timeout=timeout
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, dict) and data else None


def extract_contacts(data: dict) -> dict:
    """Телефоны/e-mail/сайт/статус из ответа Checko."""
    info: dict = {"phones": [], "emails": [], "website": None}

    for value in deep_find(data, ("Тел", "Телефон")):
        for text in _strings(value):
            for phone in extract_phones(text):
                if phone not in info["phones"]:
                    info["phones"].append(phone)

    for value in deep_find(data, ("Емэйл", "Емейл", "Email", "E-mail", "ЭлПочта", "Почта")):
        for text in _strings(value):
            for email in extract_emails(text):
                if email not in info["emails"]:
                    info["emails"].append(email)

    # Полный юридический адрес тоже есть в ответе Checko — забираем
    for value in deep_find(data, ("АдресРФ",)):
        for text in _strings(value):
            if text.strip():
                info["address"] = text.strip()
                break
        if info.get("address"):
            break

    for value in deep_find(data, ("Сайт", "ВебСайт")):
        for text in _strings(value):
            text = text.strip()
            if text and "." in text:
                info["website"] = text
                break
        if info["website"]:
            break

    for value in deep_find(data, ("Статус",)):
        for text in _strings(value):
            lowered = text.lower()
            if "действ" in lowered:
                info["is_active"] = 1
                info["egrul_status"] = text
                break
            if "ликвид" in lowered or "прекра" in lowered or "исключ" in lowered:
                info["is_active"] = 0
                info["egrul_status"] = text
                break
        if "is_active" in info:
            break

    return info


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, (dict, list)):
        for _key, leaf in walk(value):
            if isinstance(leaf, str):
                yield leaf
