"""Checko.ru: карточка компании по ИНН (реквизиты, контакты, руководитель).

Агрегирует ЕГРЮЛ, Росстат, ФНС и открытые контакты. Требует ключ:
https://checko.ru/api — есть бесплатный лимит.
"""
from __future__ import annotations

from ..models import Finding
from ..normalize import (
    normalize_company_name, normalize_domain, normalize_email, normalize_phone,
    validate_inn,
)
from .base import Context, Source

API_URL = "https://api.checko.ru/v2/company"


def _first(data: dict, *names: str):
    for name in names:
        if isinstance(data, dict) and data.get(name) not in (None, "", [], {}):
            return data[name]
    return None


class CheckoSource(Source):
    name = "checko"
    title = "Checko.ru (карточка компании)"
    reliability = 0.85
    needs_keys = ("CHECKO_KEY",)

    def input_signature(self, ctx: Context) -> str:
        return f"{ctx.inn() or ''}|{ctx.query.ogrn or ''}"

    async def run(self, ctx: Context) -> list[Finding]:
        identifier = ctx.inn() or ctx.query.ogrn
        if not identifier:
            return []
        params = {"key": ctx.config.key("CHECKO_KEY"),
                  "inn" if len(identifier) in (10, 12) else "ogrn": identifier}
        payload = await ctx.fetcher.get_json(API_URL, params=params, check_robots=False)
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if not isinstance(data, dict):
            return []

        out: list[Finding] = []
        conf = self.reliability
        for value in (_first(data, "НаимПолнЮЛ", "НаимПолн"), _first(data, "НаимСокрЮЛ", "НаимСокр")):
            name = normalize_company_name(value or "")
            if name:
                out.append(self.finding("name", name, url=API_URL, confidence=conf))
        inn = _first(data, "ИНН")
        if inn and validate_inn(str(inn)):
            out.append(self.finding("inn", str(inn), url=API_URL, confidence=conf))
        for key, kind in (("ОГРН", "ogrn"), ("КПП", "kpp"), ("ОКПО", "okpo")):
            value = _first(data, key)
            if value:
                out.append(self.finding(kind, str(value), url=API_URL, confidence=conf))
        address = _first(data, "ЮрАдрес") or {}
        address_value = address.get("АдресРФ") if isinstance(address, dict) else address
        if address_value:
            out.append(self.finding("address", str(address_value), url=API_URL,
                                    confidence=conf, address_type="legal"))
        head = _first(data, "Руковод") or {}
        if isinstance(head, dict):
            for item in (head.values() if all(isinstance(v, dict) for v in head.values()) else [head]):
                if isinstance(item, dict) and item.get("ФИО"):
                    out.append(self.finding("person", str(item["ФИО"]), url=API_URL,
                                            confidence=conf, position=item.get("НаимДолжн"),
                                            role="руководитель"))
        contacts = _first(data, "Контакты") or {}
        if isinstance(contacts, dict):
            for phone in contacts.get("Тел") or []:
                value = normalize_phone(str(phone), ctx.config.country)
                if value:
                    out.append(self.finding("phone", value, url=API_URL, confidence=0.7))
            for email in contacts.get("Емэйл") or []:
                value = normalize_email(str(email))
                if value:
                    out.append(self.finding("email", value, url=API_URL, confidence=0.7))
            site = contacts.get("ВебСайт")
            if site:
                domain = normalize_domain(str(site))
                if domain:
                    out.append(self.finding("domain", domain, url=API_URL, confidence=0.7))
        status = _first(data, "Статус")
        if isinstance(status, dict) and status.get("Наим"):
            out.append(self.finding("fact", f"статус в реестре: {status['Наим']}", url=API_URL,
                                    confidence=conf, kind_hint="status"))
        return out
