"""Certificate Transparency (crt.sh): поддомены из публичных TLS-сертификатов.

Каждый выпущенный сертификат публикуется в открытых CT-логах. Оттуда виден
список поддоменов — почтовые шлюзы, CRM, порталы для сотрудников, тестовые
стенды. Это открытые данные, но они хорошо показывают инфраструктуру компании.
"""
from __future__ import annotations

from ..models import Finding
from ..normalize import normalize_domain, registrable_domain
from .base import Context, Source

CRTSH_URL = "https://crt.sh/"
MAX_SUBDOMAINS = 40


class CrtShSource(Source):
    name = "crtsh"
    title = "Certificate Transparency (crt.sh)"
    reliability = 0.8

    def input_signature(self, ctx: Context) -> str:
        return "|".join(ctx.domains())

    async def run(self, ctx: Context) -> list[Finding]:
        out: list[Finding] = []
        for domain in ctx.domains()[:2]:
            root = registrable_domain(domain)
            data = await ctx.fetcher.get_json(
                CRTSH_URL, params={"q": f"%.{root}", "output": "json"}, check_robots=False
            )
            if not isinstance(data, list):
                continue
            seen: set[str] = set()
            for row in data:
                for raw in str(row.get("name_value", "")).splitlines():
                    host = normalize_domain(raw.strip().lstrip("*."))
                    if not host or host in seen:
                        continue
                    if registrable_domain(host) != root:
                        continue
                    seen.add(host)
                    if len(seen) > MAX_SUBDOMAINS:
                        break
                if len(seen) > MAX_SUBDOMAINS:
                    break
            for host in sorted(seen):
                out.append(self.finding(
                    "domain", host, url=f"{CRTSH_URL}?q=%25.{root}",
                    note="сертификат в CT-логах", confidence=0.7 if host != root else 0.85,
                    subdomain=host != root,
                ))
        return out
