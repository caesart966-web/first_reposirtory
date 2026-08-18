"""RDAP (современная замена WHOIS поверх HTTPS): регистратор, даты, контакты.

Для доменов .ru/.рф RDAP не поддерживается координатором, и данные регистранта
скрыты по закону о персональных данных — источник вернёт пусто. Для gTLD
(.com/.net/.io и др.) отдаёт регистратора, даты создания и abuse-контакты.
"""
from __future__ import annotations

import asyncio

from ..models import Finding
from ..normalize import normalize_email, normalize_phone
from .base import Context, Source

RDAP_ENDPOINT = "https://rdap.org/domain/{domain}"


class RdapSource(Source):
    name = "rdap"
    title = "RDAP/WHOIS домена"
    reliability = 0.85

    def input_signature(self, ctx: Context) -> str:
        return "|".join(ctx.domains())

    async def run(self, ctx: Context) -> list[Finding]:
        domains = ctx.domains()[:3]
        if not domains:
            return []
        chunks = await asyncio.gather(*(self._for_domain(ctx, d) for d in domains))
        return [f for chunk in chunks for f in chunk]

    async def _for_domain(self, ctx: Context, domain: str) -> list[Finding]:
        url = RDAP_ENDPOINT.format(domain=domain)
        data = await ctx.fetcher.get_json(url, check_robots=False)
        if not isinstance(data, dict):
            return []
        out: list[Finding] = []
        for event in data.get("events", []) or []:
            action = event.get("eventAction")
            date = (event.get("eventDate") or "")[:10]
            if action in ("registration", "expiration") and date:
                label = "дата регистрации домена" if action == "registration" else "домен оплачен до"
                out.append(self.finding("fact", f"{label} {domain}: {date}", url=url,
                                        confidence=0.9, kind_hint=action))
        for entity in data.get("entities", []) or []:
            roles = entity.get("roles") or []
            vcard = entity.get("vcardArray") or []
            fields = vcard[1] if len(vcard) > 1 and isinstance(vcard[1], list) else []
            for field in fields:
                if not isinstance(field, list) or len(field) < 4:
                    continue
                prop, value = field[0], field[3]
                if not isinstance(value, str):
                    continue
                if prop == "fn" and "registrar" in roles:
                    out.append(self.finding("fact", f"регистратор {domain}: {value}", url=url,
                                            confidence=0.9, kind_hint="registrar"))
                elif prop == "fn" and "registrant" in roles:
                    out.append(self.finding("name", value, url=url, note="registrant RDAP",
                                            confidence=0.7))
                elif prop == "org" and "registrant" in roles:
                    out.append(self.finding("name", value, url=url, note="org RDAP",
                                            confidence=0.7))
                elif prop == "email":
                    email = normalize_email(value)
                    if email:
                        is_abuse = "abuse" in roles or email.startswith("abuse@")
                        out.append(self.finding(
                            "email", email, url=url, note=f"RDAP {'/'.join(roles) or 'contact'}",
                            confidence=0.35 if is_abuse else 0.7, rdap_role="/".join(roles),
                        ))
                elif prop == "tel":
                    phone = normalize_phone(value.replace("tel:", ""), ctx.config.country)
                    if phone and "registrar" not in roles:
                        out.append(self.finding("phone", phone, url=url, note="RDAP контакт",
                                                confidence=0.6))
        return out
