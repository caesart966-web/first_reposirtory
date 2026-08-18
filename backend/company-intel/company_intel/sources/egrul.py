"""Прямой запрос к сервису ФНС egrul.nalog.ru (без ключей, но нестабильно).

Сервис не является документированным API: он предназначен для браузера,
периодически меняет протокол и включает защиту от автоматизации. Используется
как запасной вариант, когда нет токена DaData; при неудаче просто молчит.
"""
from __future__ import annotations

import asyncio

from ..models import Finding
from ..normalize import normalize_company_name, validate_inn, validate_ogrn
from .base import Context, Source

SEARCH_URL = "https://egrul.nalog.ru/"
RESULT_URL = "https://egrul.nalog.ru/search-result/{token}"


class EgrulSource(Source):
    name = "egrul"
    title = "ФНС: egrul.nalog.ru"
    reliability = 0.9
    legal_note = "Открытые сведения ЕГРЮЛ/ЕГРИП (ст. 6 ФЗ-129)."

    def input_signature(self, ctx: Context) -> str:
        return f"{ctx.inn()}|{'|'.join(ctx.names()[:1])}"

    async def run(self, ctx: Context) -> list[Finding]:
        # Если есть токен DaData, тот же результат приходит стабильнее — не дублируем.
        if ctx.config.key("DADATA_TOKEN"):
            return []
        query = ctx.inn() or ctx.query.ogrn or (ctx.names()[0] if ctx.names() else None)
        if not query:
            return []
        started = await ctx.fetcher.post_json(
            SEARCH_URL, data={"vyp3CaptchaToken": "", "page": "", "query": query,
                              "region": "", "PreventChromeAutocomplete": ""},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        if not isinstance(started, dict) or not started.get("t"):
            return []
        token = started["t"]
        rows: list[dict] = []
        for _ in range(6):  # сервис отвечает не сразу — опрашиваем результат
            data = await ctx.fetcher.get_json(RESULT_URL.format(token=token),
                                              use_cache=False, check_robots=False)
            if isinstance(data, dict) and data.get("rows"):
                rows = data["rows"]
                break
            await asyncio.sleep(1.5)
        out: list[Finding] = []
        for i, row in enumerate(rows[:3]):
            weight = 1.0 if i == 0 else 0.6
            out.extend(self._parse_row(row, weight))
        return out

    def _parse_row(self, row: dict, weight: float) -> list[Finding]:
        conf = self.reliability * weight
        out: list[Finding] = []
        url = SEARCH_URL
        name = normalize_company_name(row.get("n") or row.get("c") or "")
        if name:
            out.append(self.finding("name", name, url=url, note="ЕГРЮЛ", confidence=conf))
        inn = row.get("i")
        if inn and validate_inn(str(inn)):
            out.append(self.finding("inn", str(inn), url=url, note="ЕГРЮЛ", confidence=conf))
        ogrn = row.get("o")
        if ogrn and validate_ogrn(str(ogrn)):
            out.append(self.finding("ogrn", str(ogrn), url=url, note="ЕГРЮЛ", confidence=conf))
        if row.get("k"):
            out.append(self.finding("kpp", str(row["k"]), url=url, confidence=conf))
        if row.get("a"):
            out.append(self.finding("address", str(row["a"]), url=url,
                                    note="юридический адрес", confidence=conf,
                                    address_type="legal"))
        if row.get("g"):
            out.append(self.finding("person", str(row["g"]), url=url, confidence=conf,
                                    role="руководитель"))
        if row.get("e"):
            out.append(self.finding("fact", f"дата регистрации: {row['e']}", url=url,
                                    confidence=conf, kind_hint="registration_date"))
        return out
