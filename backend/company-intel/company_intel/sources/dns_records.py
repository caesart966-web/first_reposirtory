"""DNS: MX, TXT/SPF, NS. Показывает почтового провайдера и связанные домены.

Зачем: MX-запись говорит, куда реально уходит почта (Яндекс 360, Google
Workspace, свой сервер), а `include:` в SPF часто раскрывает смежные домены
и сервисы рассылок компании.
"""
from __future__ import annotations

import asyncio
import re

from ..models import Finding
from ..normalize import normalize_domain
from .base import Context, Source

try:
    import dns.resolver  # type: ignore
    HAS_DNSPYTHON = True
except ImportError:  # pragma: no cover
    HAS_DNSPYTHON = False

MAIL_PROVIDERS = {
    "mx.yandex.net": "Яндекс 360", "mx.yandex.ru": "Яндекс 360",
    "google.com": "Google Workspace", "googlemail.com": "Google Workspace",
    "outlook.com": "Microsoft 365", "protection.outlook.com": "Microsoft 365",
    "mail.ru": "VK WorkMail", "biz.mail.ru": "VK WorkMail",
    "zoho.com": "Zoho Mail", "beget.com": "Beget", "timeweb.ru": "Timeweb",
    "reg.ru": "REG.RU", "nic.ru": "RU-CENTER",
}


def _provider(host: str) -> str | None:
    host = host.lower().rstrip(".")
    for suffix, title in MAIL_PROVIDERS.items():
        if host == suffix or host.endswith("." + suffix):
            return title
    return None


class DnsSource(Source):
    name = "dns"
    title = "DNS-записи домена"
    reliability = 0.9

    def input_signature(self, ctx: Context) -> str:
        return "|".join(ctx.domains())

    async def run(self, ctx: Context) -> list[Finding]:
        domains = ctx.domains()[:3]
        if not domains:
            return []
        if not HAS_DNSPYTHON:
            return []
        chunks = await asyncio.gather(*(self._for_domain(d) for d in domains))
        return [f for chunk in chunks for f in chunk]

    async def _for_domain(self, domain: str) -> list[Finding]:
        out: list[Finding] = []
        mx = await self._query(domain, "MX")
        for record in mx:
            host = str(record).split()[-1].rstrip(".")
            provider = _provider(host)
            out.append(self.finding(
                "fact", f"почтовый сервер: {host}" + (f" ({provider})" if provider else ""),
                note=f"MX {domain}", confidence=0.9,
                kind_hint="mail_server", domain=domain, provider=provider,
            ))
        txt = await self._query(domain, "TXT")
        for record in txt:
            value = str(record).strip('"')
            if not value.lower().startswith("v=spf1"):
                continue
            out.append(self.finding("fact", f"SPF: {value[:300]}", note=f"TXT {domain}",
                                    confidence=0.85, kind_hint="spf"))
            for included in re.findall(r"include:([\w.-]+)", value):
                related = normalize_domain(included)
                if related and related != domain:
                    out.append(self.finding("domain", related, note=f"SPF include у {domain}",
                                            confidence=0.4, relation="spf_include"))
        ns = await self._query(domain, "NS")
        for record in ns:
            host = str(record).rstrip(".")
            out.append(self.finding("fact", f"NS: {host}", note=f"NS {domain}",
                                    confidence=0.8, kind_hint="ns"))
        return out

    async def _query(self, domain: str, rtype: str) -> list:
        def _run():
            try:
                resolver = dns.resolver.Resolver()
                resolver.lifetime = 8.0
                return list(resolver.resolve(domain, rtype))
            except Exception:
                return []
        return await asyncio.to_thread(_run)
