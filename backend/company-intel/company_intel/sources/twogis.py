"""2ГИС Catalog API: карточка организации в справочнике.

Справочник полезен там, где у компании нет сайта: телефон, адрес, часы работы
и ссылка на сайт заполняются самой компанией. Ключ: https://dev.2gis.ru/
"""
from __future__ import annotations

from ..models import Finding
from ..normalize import (
    normalize_company_name, normalize_domain, normalize_email, normalize_phone,
)
from .base import Context, Source

API_URL = "https://catalog.api.2gis.com/3.0/items"
FIELDS = "items.contact_groups,items.address,items.full_address_name,items.schedule"


class TwoGisSource(Source):
    name = "2gis"
    title = "2ГИС (справочник организаций)"
    reliability = 0.75
    needs_keys = ("TWOGIS_KEY",)

    def input_signature(self, ctx: Context) -> str:
        return f"{'|'.join(ctx.names()[:1])}|{ctx.query.city or ''}"

    async def run(self, ctx: Context) -> list[Finding]:
        names = ctx.names()
        if not names:
            return []
        query = names[0] + (f" {ctx.query.city}" if ctx.query.city else "")
        data = await ctx.fetcher.get_json(
            API_URL,
            params={"q": query, "key": ctx.config.key("TWOGIS_KEY"),
                    "fields": FIELDS, "page_size": 5, "locale": "ru_RU"},
            check_robots=False,
        )
        if not isinstance(data, dict):
            return []
        items = ((data.get("result") or {}).get("items")) or []
        out: list[Finding] = []
        for index, item in enumerate(items[:3]):
            weight = 1.0 if index == 0 else 0.6
            conf = self.reliability * weight
            name = normalize_company_name(item.get("name") or "")
            if name:
                out.append(self.finding("name", name, url=API_URL, note="2ГИС", confidence=conf * 0.8))
            address = item.get("full_address_name") or (item.get("address") or {}).get("name")
            if address:
                out.append(self.finding("address", str(address), url=API_URL, note="2ГИС",
                                        confidence=conf, address_type="fact"))
            for group in item.get("contact_groups") or []:
                for contact in group.get("contacts") or []:
                    ctype, value = contact.get("type"), contact.get("value")
                    if not value:
                        continue
                    if ctype == "phone":
                        phone = normalize_phone(str(value), ctx.config.country)
                        if phone:
                            out.append(self.finding("phone", phone, url=API_URL, note="2ГИС",
                                                    confidence=conf))
                    elif ctype == "email":
                        email = normalize_email(str(value))
                        if email:
                            out.append(self.finding("email", email, url=API_URL, note="2ГИС",
                                                    confidence=conf))
                    elif ctype == "website":
                        domain = normalize_domain(str(value))
                        if domain:
                            out.append(self.finding("domain", domain, url=API_URL, note="2ГИС",
                                                    confidence=conf))
                    elif ctype in ("vkontakte", "telegram", "whatsapp", "instagram", "facebook"):
                        link = contact.get("url") or value
                        out.append(self.finding("social", str(link), url=API_URL, note="2ГИС",
                                                confidence=conf * 0.9, network=ctype))
            schedule = item.get("schedule")
            if isinstance(schedule, dict) and schedule.get("comment"):
                out.append(self.finding("fact", f"режим работы: {schedule['comment']}",
                                        url=API_URL, confidence=conf * 0.8, kind_hint="schedule"))
        return out
