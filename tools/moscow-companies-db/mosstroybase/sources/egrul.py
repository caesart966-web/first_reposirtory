"""ЕГРЮЛ через бесплатное JSON-зеркало egrul.itsoft.ru.

Даёт: полное/краткое наименование, статус (действует/ликвидировано),
адрес, ОКВЭД, e-mail (поле СвАдрЭлПочты) и, изредка, контактный телефон.
Телефонов в ЕГРЮЛ почти нет — их добирают Checko и сайты компаний.

Формат зеркала — JSON-конвертация выписки ЕГРЮЛ; точная структура ключей
меняется от записи к записи, поэтому извлечение сделано рекурсивным
обходом по «смысловым» ключам, а не жёсткими путями.
"""

from __future__ import annotations

import re
from typing import Any, Iterator

import requests

from ..config import EGRUL_JSON_URL
from ..normalize import extract_emails, extract_phones

_GUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{2}\.\d{2}\.\d{4}$")

# Ключи, значения которых не нужны в собранном адресе
_ADDRESS_SKIP_KEYS = {"КодРегион", "КодАдрКладр", "ИдНом", "КодНО", "СпосПредстСвед"}


def walk(obj: Any, parent_key: str = "") -> Iterator[tuple[str, Any]]:
    """Рекурсивно выдаёт (ключ, значение) для всех листьев JSON-структуры."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                yield from walk(value, key)
            else:
                yield key, value
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item, parent_key)


def deep_find(obj: Any, key_substrings: tuple[str, ...]) -> Iterator[Any]:
    """Все значения (включая поддеревья), чей ключ содержит одну из подстрок."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if any(s in key for s in key_substrings):
                yield value
            if isinstance(value, (dict, list)):
                yield from deep_find(value, key_substrings)
    elif isinstance(obj, list):
        for item in obj:
            yield from deep_find(item, key_substrings)


def _first_str(values: Iterator[Any]) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def fetch(inn: str, session: requests.Session, timeout: int = 30) -> dict | None:
    """Запись ЕГРЮЛ по ИНН; None, если не найдена (404)."""
    resp = session.get(EGRUL_JSON_URL.format(inn=inn), timeout=timeout)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, dict) and data else None


def extract_info(payload: dict) -> dict:
    """Вытаскивает из записи ЕГРЮЛ поля для базы."""
    info: dict = {}

    info["name"] = _first_str(deep_find(payload, ("НаимЮЛПолн",)))
    info["name_short"] = _first_str(deep_find(payload, ("НаимЮЛСокр", "СокрНаим")))
    info["ogrn"] = _first_str(deep_find(payload, ("ОГРН",)))

    # Статус: наличие блока СвПрекрЮЛ означает прекращение деятельности
    terminated = any(True for _ in deep_find(payload, ("СвПрекрЮЛ",)))
    status_name = _first_str(deep_find(payload, ("НаимСтатусЮЛ",)))
    info["is_active"] = 0 if terminated else 1
    info["egrul_status"] = status_name or ("Прекратило деятельность" if terminated else "Действует")

    # e-mail: только из полей про электронную почту
    emails: list[str] = []
    for value in deep_find(payload, ("ЭлПочт", "E-mail", "Email")):
        for text in _leaf_strings(value):
            for email in extract_emails(text):
                if email not in emails:
                    emails.append(email)
    info["emails"] = emails

    # Телефон встречается редко (ключи с "Тлф")
    phones: list[str] = []
    for value in deep_find(payload, ("Тлф",)):
        for text in _leaf_strings(value):
            for phone in extract_phones(text):
                if phone not in phones:
                    phones.append(phone)
    info["phones"] = phones

    # Адрес: собираем строковые листья адресных блоков, отбрасывая коды/GUID/даты
    for address_block in deep_find(payload, ("АдресЮЛ", "АдрЮЛ")):
        parts: list[str] = []
        for key, value in walk(address_block):
            if not isinstance(value, str):
                continue
            value = value.strip()
            if (
                not value
                or key in _ADDRESS_SKIP_KEYS
                or _GUID_RE.match(value)
                or _DATE_RE.match(value)
            ):
                continue
            if value not in parts:
                parts.append(value)
        if parts:
            info["address"] = ", ".join(parts)
            break

    info["region_code"] = _first_str(deep_find(payload, ("КодРегион",)))

    # ОКВЭД (пригодится для компаний, добавленных вручную по ИНН)
    for block in deep_find(payload, ("СвОКВЭДОсн",)):
        code = _first_str(deep_find({"x": block}, ("КодОКВЭД",)))
        if code:
            info["okved_main"] = code
            break
    okved_add: list[str] = []
    for block in deep_find(payload, ("СвОКВЭДДоп",)):
        for value in deep_find({"x": block}, ("КодОКВЭД",)):
            if isinstance(value, str) and value not in okved_add:
                okved_add.append(value)
    info["okved_add"] = okved_add

    return info


def _leaf_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, (dict, list)):
        for _key, leaf in walk(value):
            if isinstance(leaf, str):
                yield leaf
