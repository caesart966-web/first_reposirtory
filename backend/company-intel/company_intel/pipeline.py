"""Оркестратор: раскручивает клубок от известных данных к новым.

Логика раундов важнее самих источников. В первом раунде работают те, кому
хватает входных данных пользователя. Найденный домен открывает DNS, RDAP,
сертификаты и обход сайта; найденное ФИО директора — гипотезы адресов;
найденный ИНН — точную карточку из реестра. Поэтому источники запускаются
повторно, пока их входные данные меняются.
"""
from __future__ import annotations

import asyncio
import logging
import time

from .config import Config
from .http import Fetcher
from .merge import FREEMAIL, apply_relevance, merge_findings
from .models import Finding, Profile, Provenance, Query, utcnow
from .normalize import (
    email_domain, normalize_domain, normalize_email, normalize_inn,
    normalize_ogrn, normalize_phone, normalize_company_name,
)
from .sources import Context, available_sources

log = logging.getLogger("company_intel.pipeline")


def seed_findings(query: Query) -> tuple[list[Finding], list[str]]:
    """Превращает исходные данные пользователя в находки. Заодно проверяет их."""
    prov = Provenance(source="input", note="данные от пользователя")
    out: list[Finding] = []
    warnings: list[str] = []

    if query.name:
        name = normalize_company_name(query.name)
        if name:
            out.append(Finding("name", name, prov, 0.85))
    if query.inn:
        inn = normalize_inn(query.inn)
        if inn:
            out.append(Finding("inn", inn, prov, 0.95))
        else:
            warnings.append(f"ИНН «{query.inn}» не проходит проверку контрольной суммы")
    if query.ogrn:
        ogrn = normalize_ogrn(query.ogrn)
        if ogrn:
            out.append(Finding("ogrn", ogrn, prov, 0.95))
        else:
            warnings.append(f"ОГРН «{query.ogrn}» не проходит проверку контрольной суммы")
    if query.domain:
        domain = normalize_domain(query.domain)
        if domain:
            query.domain = domain
            out.append(Finding("domain", domain, prov, 0.9))
        else:
            warnings.append(f"домен «{query.domain}» не распознан")
    if query.email:
        email = normalize_email(query.email)
        if email:
            out.append(Finding("email", email, prov, 0.9))
            host = normalize_domain(email_domain(email))
            if host and host not in FREEMAIL and not query.domain:
                query.domain = host
                out.append(Finding("domain", host, Provenance(
                    source="input", note="домен из адреса почты"), 0.7))
        else:
            warnings.append(f"почта «{query.email}» не распознана")
    if query.phone:
        phone = normalize_phone(query.phone, query.country)
        if phone:
            query.phone = phone
            out.append(Finding("phone", phone, prov, 0.9))
        else:
            warnings.append(f"телефон «{query.phone}» не распознан")
    if query.person:
        out.append(Finding("person", query.person, prov, 0.8, {"role": "из запроса"}))
    return out, warnings


async def run_pipeline(
    query: Query, config: Config | None = None, fetcher: Fetcher | None = None,
) -> Profile:
    """Полный прогон: сбор → слияние → оценка релевантности.

    `fetcher` можно передать снаружи (тесты, свой пул соединений) — тогда его
    жизненным циклом управляет вызывающая сторона.
    """
    config = config or Config.from_env()
    started = time.monotonic()
    profile = Profile(query=query)

    findings, warnings = seed_findings(query)
    profile.warnings.extend(warnings)
    if query.is_empty():
        profile.warnings.append("не задано ни одного исходного признака компании")
        profile.finished_at = utcnow()
        return profile

    sources, skipped = available_sources(config)
    if not sources:
        profile.warnings.append("нет доступных источников — проверьте ключи и настройки")
    for name, reason in skipped:
        profile.warnings.append(f"источник {name} пропущен: {reason}")

    per_source_stats: dict[str, int] = {}
    signatures: dict[str, str] = {}
    rounds_done = 0

    external_fetcher = fetcher is not None
    fetcher = fetcher or Fetcher(
        timeout=config.timeout,
        per_host_delay=config.per_host_delay,
        max_concurrency=config.max_concurrency,
        respect_robots=config.respect_robots,
        cache_path=config.cache_path,
        cache_ttl=config.cache_ttl,
    )
    try:
        for round_index in range(config.max_rounds):
            merged = merge_findings(findings)
            ctx = Context(query=query, config=config, fetcher=fetcher,
                          known=merged, round=round_index)

            batch = []
            for source in sources:
                signature = source.input_signature(ctx)
                if not signature.strip("|"):
                    continue  # источнику нечего взять на вход
                if signatures.get(source.name) == signature:
                    continue  # входные данные не изменились — повтор не нужен
                signatures[source.name] = signature
                batch.append(source)

            if not batch:
                break
            rounds_done = round_index + 1
            log.info("раунд %s: %s", round_index + 1, ", ".join(s.name for s in batch))
            results = await asyncio.gather(
                *(_run_source(source, ctx) for source in batch), return_exceptions=True
            )
            for source, result in zip(batch, results):
                if isinstance(result, BaseException):
                    profile.warnings.append(f"источник {source.name} упал: {result}")
                    log.warning("источник %s упал", source.name, exc_info=result)
                    continue
                per_source_stats[source.name] = per_source_stats.get(source.name, 0) + len(result)
                findings.extend(result)

        http_stats = dict(fetcher.stats)
    finally:
        if not external_fetcher:
            await fetcher.aclose()

    profile.attributes = merge_findings(findings)
    profile.warnings.extend(apply_relevance(profile.attributes, query))
    profile.stats = {
        "findings": len(findings),
        "by_source": per_source_stats,
        "http": http_stats,
        "duration_sec": round(time.monotonic() - started, 2),
        "rounds": rounds_done,
    }
    profile.finished_at = utcnow()
    return profile


async def _run_source(source, ctx: Context) -> list[Finding]:
    try:
        return await source.run(ctx)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # источник не должен ронять весь прогон
        log.warning("ошибка источника %s: %s", source.name, exc)
        raise
