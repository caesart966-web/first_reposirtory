"""Hunter.io: корпоративные адреса по домену, с именами и должностями.

Коммерческий сервис, который сам собирает адреса из открытых источников и
хранит подтверждения. Требует ключ: https://hunter.io/api-keys
"""
from __future__ import annotations

from ..models import Finding
from ..normalize import normalize_email
from .base import Context, Source

DOMAIN_SEARCH = "https://api.hunter.io/v2/domain-search"


class HunterSource(Source):
    name = "hunter"
    title = "Hunter.io (адреса по домену)"
    reliability = 0.8
    needs_keys = ("HUNTER_API_KEY",)

    def input_signature(self, ctx: Context) -> str:
        return "|".join(ctx.domains()[:1])

    async def run(self, ctx: Context) -> list[Finding]:
        domains = ctx.domains()[:1]
        if not domains:
            return []
        data = await ctx.fetcher.get_json(
            DOMAIN_SEARCH,
            params={"domain": domains[0], "api_key": ctx.config.key("HUNTER_API_KEY"),
                    "limit": 50},
            check_robots=False,
        )
        if not isinstance(data, dict):
            return []
        payload = data.get("data") or {}
        out: list[Finding] = []
        if payload.get("organization"):
            out.append(self.finding("name", payload["organization"], url=DOMAIN_SEARCH,
                                    confidence=0.6))
        if payload.get("pattern"):
            out.append(self.finding("fact", f"шаблон корпоративной почты: {payload['pattern']}",
                                    url=DOMAIN_SEARCH, confidence=0.7, kind_hint="email_pattern"))
        for item in payload.get("emails", []) or []:
            email = normalize_email(item.get("value") or "")
            if not email:
                continue
            # Hunter отдаёт свою оценку 0..100 — переводим в нашу шкалу.
            score = float(item.get("confidence") or 50) / 100.0
            fio = " ".join(x for x in (item.get("first_name"), item.get("last_name")) if x)
            out.append(self.finding(
                "email", email, url=DOMAIN_SEARCH, note="Hunter.io",
                confidence=min(0.9, self.reliability * max(0.2, score)),
                person=fio or None, position=item.get("position"),
                email_type=item.get("type"), verified=item.get("verification", {}).get("status"),
            ))
            if fio:
                out.append(self.finding("person", fio, url=DOMAIN_SEARCH, confidence=0.5,
                                        position=item.get("position"), email=email))
        return out
