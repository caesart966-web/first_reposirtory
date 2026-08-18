"""Гипотезы корпоративных адресов по ФИО и домену.

Это НЕ найденные данные, а предположения: «если в компании принят шаблон
i.familiya@domain, то у Иванова адрес такой». Отдаются с низкой уверенностью и
меткой `hypothesis`, в отчёте попадают в отдельный раздел. Включается флагом
`--guess-emails`.

Проверка ограничена наличием MX-записи у домена. SMTP-опрос (RCPT TO) намеренно
не делается: он создаёт нагрузку на чужой почтовый сервер, часто блокируется и
приводит к попаданию IP в чёрные списки.
"""
from __future__ import annotations

import asyncio

from ..models import Finding
from ..normalize import normalize_email, translit_ru
from .base import Context, Source

try:
    import dns.resolver  # type: ignore
    HAS_DNSPYTHON = True
except ImportError:  # pragma: no cover
    HAS_DNSPYTHON = False


def patterns_for(first: str, last: str) -> list[str]:
    """Наиболее частые шаблоны корпоративных адресов."""
    f, l = first.lower(), last.lower()
    if not f or not l:
        return [x for x in (f, l) if x]
    return [f"{f[0]}.{l}", f"{f}.{l}", l, f"{f[0]}{l}", f"{f}_{l}", f"{f}", f"{l}.{f[0]}"]


class EmailGuessSource(Source):
    name = "email_guess"
    title = "Гипотезы адресов по шаблону"
    reliability = 0.2

    def available(self, config) -> tuple[bool, str]:
        if not config.allow_email_guessing:
            return False, "выключено (включается флагом --guess-emails)"
        return super().available(config)

    def input_signature(self, ctx: Context) -> str:
        return "|".join(ctx.domains()[:1] + ctx.persons())

    async def run(self, ctx: Context) -> list[Finding]:
        domains = ctx.domains()[:1]
        persons = ctx.persons()
        if not domains or not persons:
            return []
        domain = domains[0]
        has_mx = await self._has_mx(domain)

        known_pattern = None
        for attr in ctx.known.get("fact", []):
            if attr.extra.get("kind_hint") == "email_pattern":
                known_pattern = attr.value
                break

        out: list[Finding] = []
        for fio in persons[:5]:
            parts = [p for p in fio.replace("ё", "е").split() if p]
            if len(parts) < 2:
                continue
            a, b = translit_ru(parts[0]), translit_ru(parts[1])
            # Порядок слов заранее неизвестен: «Иванов Сергей» и «Сергей Иванов»
            # встречаются одинаково часто, поэтому берём обе трактовки.
            locals_ = patterns_for(b, a)
            if len(parts) == 2:
                locals_ += [x for x in patterns_for(a, b) if x not in locals_]
            for local in locals_:
                email = normalize_email(f"{local}@{domain}")
                if not email:
                    continue
                out.append(self.finding(
                    "email", email, note=f"гипотеза по шаблону для «{fio}»",
                    confidence=0.22 if has_mx else 0.12,
                    hypothesis=True, person=fio, mx_present=has_mx,
                    known_pattern=known_pattern,
                ))
        return out

    async def _has_mx(self, domain: str) -> bool:
        if not HAS_DNSPYTHON:
            return False

        def _run() -> bool:
            try:
                resolver = dns.resolver.Resolver()
                resolver.lifetime = 6.0
                return bool(list(resolver.resolve(domain, "MX")))
            except Exception:
                return False
        return await asyncio.to_thread(_run)
