"""Оркестратор: гоняет каждую компанию по всем источникам и копит находки.

Останавливается по источникам рано, если уже есть подтверждённый ИНН-контакт,
чтобы не долбить сеть зря. Устойчив к падению любого источника — ошибка
одного не рушит обработку компании.
"""
from __future__ import annotations

import concurrent.futures as futures

from .config import Config
from .secrets import scrub
from .http import Fetcher
from .models import Company
from .sources import SOURCES


def process_company(company: Company, cfg: Config) -> Company:
    """Пробить одну компанию по всем источникам."""
    fetcher = Fetcher(
        delay=cfg.delay,
        timeout=cfg.timeout,
        retries=cfg.retries,
        proxy=cfg.proxy,
        verbose=cfg.verbose,
    )
    for source in SOURCES:
        try:
            company.findings.extend(source(company, fetcher, cfg))
        except Exception as exc:  # noqa: BLE001
            if cfg.verbose:
                print(scrub(f"    ! источник {source.__name__} упал: {exc}"))
        # Достаточно, если уже есть надёжный телефон.
        if company.phones:
            break
    return company


def run(companies: list[Company], cfg: Config, workers: int = 1, progress=None) -> None:
    """Обработать список. workers>1 — параллельно (каждый со своим Fetcher).

    По умолчанию workers=1: бережём хосты от лавины запросов. Наращивать
    стоит осторожно и только с прокси-пулом.
    """
    if workers <= 1:
        for i, company in enumerate(companies, 1):
            process_company(company, cfg)
            if progress:
                progress(i, len(companies), company)
        return

    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(process_company, c, cfg): c for c in companies}
        done = 0
        for future in futures.as_completed(future_map):
            done += 1
            company = future_map[future]
            try:
                future.result()
            except Exception:  # noqa: BLE001
                pass
            if progress:
                progress(done, len(companies), company)
