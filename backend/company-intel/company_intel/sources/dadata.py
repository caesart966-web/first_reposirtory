"""DaData: официальные реквизиты из ЕГРЮЛ/ЕГРИП по ИНН, ОГРН или названию.

Даёт полное наименование, адрес, руководителя, ОКВЭД, статус (действующая /
ликвидирована), дату регистрации. Требует бесплатный токен (10 000 запросов
в сутки): https://dadata.ru/api/find-party/
"""
from __future__ import annotations

from ..models import Finding
from ..normalize import (
    normalize_company_name, normalize_email, normalize_phone, validate_inn,
)
from .base import Context, Source

FIND_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"


class DaDataSource(Source):
    name = "dadata"
    title = "DaData (ЕГРЮЛ/ЕГРИП)"
    reliability = 0.95
    needs_keys = ("DADATA_TOKEN",)
    legal_note = "Официальные данные госреестра, распространяются свободно."

    def input_signature(self, ctx: Context) -> str:
        return f"{ctx.inn()}|{'|'.join(ctx.names())}|{ctx.query.ogrn or ''}"

    async def run(self, ctx: Context) -> list[Finding]:
        token = ctx.config.key("DADATA_TOKEN")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {token}",
        }
        identifier = ctx.inn() or ctx.query.ogrn
        payload: dict
        url: str
        if identifier:
            url, payload = FIND_URL, {"query": identifier, "count": 5}
        elif ctx.names():
            url, payload = SUGGEST_URL, {"query": ctx.names()[0], "count": 5}
            if ctx.query.city:
                payload["query"] += f" {ctx.query.city}"
        else:
            return []

        data = await ctx.fetcher.post_json(url, json_body=payload, headers=headers)
        if not isinstance(data, dict):
            return []
        out: list[Finding] = []
        for i, item in enumerate(data.get("suggestions", [])[:3]):
            # Первое совпадение самое релевантное; дальше уверенность падает.
            weight = 1.0 if i == 0 else 0.6
            out.extend(self._parse_party(item, url, weight))
        return out

    def _parse_party(self, item: dict, url: str, weight: float) -> list[Finding]:
        out: list[Finding] = []
        data = item.get("data") or {}
        conf = self.reliability * weight

        for value in (item.get("value"), (data.get("name") or {}).get("full_with_opf")):
            name = normalize_company_name(value or "")
            if name:
                out.append(self.finding("name", name, url=url, note="ЕГРЮЛ", confidence=conf))
        inn = data.get("inn")
        if inn and validate_inn(inn):
            out.append(self.finding("inn", inn, url=url, note="ЕГРЮЛ", confidence=conf))
        for kind in ("ogrn", "kpp", "okpo"):
            value = data.get(kind)
            if value:
                out.append(self.finding(kind, str(value), url=url, note="ЕГРЮЛ", confidence=conf))
        address = (data.get("address") or {}).get("unrestricted_value")
        if address:
            out.append(self.finding("address", address, url=url, note="юридический адрес",
                                    confidence=conf, address_type="legal"))
        management = data.get("management") or {}
        if management.get("name"):
            out.append(self.finding("person", management["name"], url=url,
                                    confidence=conf, position=management.get("post"),
                                    role="руководитель"))
        state = (data.get("state") or {}).get("status")
        if state:
            out.append(self.finding("fact", f"статус в реестре: {state}", url=url,
                                    confidence=conf, kind_hint="status"))
        registration = (data.get("state") or {}).get("registration_date")
        if registration:
            out.append(self.finding("fact", f"дата регистрации (мс): {registration}", url=url,
                                    confidence=conf, kind_hint="registration_date"))
        okved = data.get("okved")
        if okved:
            out.append(self.finding("fact", f"основной ОКВЭД: {okved}", url=url,
                                    confidence=conf, kind_hint="okved"))
        capital = (data.get("capital") or {}).get("value")
        if capital:
            out.append(self.finding("fact", f"уставный капитал: {capital}", url=url,
                                    confidence=conf, kind_hint="capital"))
        for phone in data.get("phones") or []:
            value = normalize_phone(str(phone.get("value", "")))
            if value:
                out.append(self.finding("phone", value, url=url, note="ЕГРЮЛ", confidence=conf))
        for email in data.get("emails") or []:
            value = normalize_email(str(email.get("value", "")))
            if value:
                out.append(self.finding("email", value, url=url, note="ЕГРЮЛ", confidence=conf))
        return out
