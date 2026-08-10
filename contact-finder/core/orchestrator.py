"""Оркестратор: обходит источники по приоритету, пишет всё в базу сразу,
переживает остановку в любой точке и продолжает с последней необработанной
компании.

Ключевые механики:
- очередь компаний из SQLite (pending -> done/retry_later/error);
- обход коннекторов по приоритету с повторными проходами: если поздний
  источник нашёл домен, коннектор сайта запустится в том же цикле;
- остановка по достаточности: depth=first_email прекращает опрос источников,
  как только у компании появился валидный e-mail;
- circuit breaker: источник со стабильными ошибками ставится на паузу
  (по умолчанию 15 минут), прогон продолжается по остальным источникам;
- retry_later: компании, упёршиеся в 429/5xx, возвращаются в конец прогона;
- пауза/продолжение (для GUI) через asyncio.Event.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from connectors import build_connectors
from connectors.base import BaseConnector
from core.config import Config
from core.models import (
    Company,
    CompanyStatus,
    Contact,
    ContactType,
    SourceLevel,
)
from core.scoring import merge_and_score
from storage.db import Database
from utils.http import HttpClient
from utils.logging_setup import get_logger
from validators.email import EmailValidator, domain_of


@dataclass
class Progress:
    """Счётчики для CLI/GUI прогресс-бара."""

    total: int = 0
    processed: int = 0
    found_email: int = 0
    found_phone: int = 0
    errors: int = 0
    started_at: float = field(default_factory=time.time)

    @property
    def eta_seconds(self) -> Optional[float]:
        if self.processed == 0:
            return None
        elapsed = time.time() - self.started_at
        rate = elapsed / self.processed
        return rate * (self.total - self.processed)


ProgressCallback = Callable[[Progress, str], None]


class Orchestrator:
    """Главный пайплайн обогащения."""

    def __init__(self, config: Config, db: Database,
                 only_sources: Optional[set[str]] = None,
                 concurrency: Optional[int] = None,
                 depth: Optional[str] = None):
        self.config = config
        self.db = db
        self.log = get_logger()
        self.http = HttpClient(config, db)
        self.only_sources = only_sources
        self.concurrency = concurrency or int(config.get("http.concurrency", 10))
        self.depth = depth or str(config.get("depth", "full"))
        self.progress = Progress()
        self.pause_event = asyncio.Event()
        self.pause_event.set()          # set = работаем; clear = пауза
        self.stop_requested = False
        self._progress_cb: Optional[ProgressCallback] = None
        self._breaker_threshold = int(config.get("circuit_breaker.error_threshold", 5))
        self._breaker_pause = float(config.get("circuit_breaker.pause_minutes", 15)) * 60
        self._breaker_lock = asyncio.Lock()
        self.email_validator = EmailValidator(
            stop_prefixes=list(config.get("validation.email_stop_prefixes", [])),
            stop_addresses=list(config.get("validation.email_stop_addresses", [])),
            dev_domains=list(config.get("validation.dev_stoplist_domains", [])),
            free_domains=list(config.get("validation.free_mail_domains", [])),
            check_mx=bool(config.get("validation.check_mx", True)),
        )

    # ------------------------------------------------------------------ #

    def on_progress(self, callback: ProgressCallback) -> None:
        self._progress_cb = callback

    def _notify(self, message: str) -> None:
        if self._progress_cb:
            try:
                self._progress_cb(self.progress, message)
            except Exception:  # noqa: BLE001 — сбой UI не роняет пайплайн
                pass

    def request_stop(self) -> None:
        self.stop_requested = True
        self.pause_event.set()   # разбудить ожидающих, чтобы корректно выйти

    # ------------------------------------------------------------------ #

    async def run(self) -> Progress:
        """Обработать все компании в статусе pending/retry_later."""
        connectors = build_connectors(self.http, self.config, self.db,
                                      only=self.only_sources)
        if not connectors:
            self.log.error("Нет ни одного включённого источника — проверьте config.yaml и .env")
            return self.progress
        self.log.info("Активные источники (по приоритету): %s",
                      ", ".join(f"{c.name}({c.level.value})" for c in connectors))

        purged = self.db.cache_purge_expired(self.config.cache_ttl_seconds)
        if purged:
            self.log.debug("Очищено %d протухших записей HTTP-кэша", purged)

        await self.http.start()
        try:
            # основной проход + один проход по retry_later в конце прогона
            for wave, statuses in enumerate((
                (CompanyStatus.PENDING,),
                (CompanyStatus.RETRY_LATER,),
            )):
                companies = self.db.fetch_companies(statuses)
                if not companies:
                    continue
                if wave == 1:
                    self.log.info("Повторный проход: %d компаний со статусом retry_later",
                                  len(companies))
                self.progress.total = self.progress.processed + len(companies)
                await self._run_wave(companies, connectors)
                if self.stop_requested:
                    break
        finally:
            await self.http.close()
        return self.progress

    async def _run_wave(self, companies: list[Company],
                        connectors: list[BaseConnector]) -> None:
        queue: asyncio.Queue[Company] = asyncio.Queue()
        for company in companies:
            queue.put_nowait(company)

        async def worker() -> None:
            while not self.stop_requested:
                try:
                    company = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    await self.pause_event.wait()
                    if self.stop_requested:
                        return
                    await self.process_company(company, connectors)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001 — не роняем весь прогон
                    self.log.exception("[%s] Необработанный сбой", company.key)
                    self.db.mark_company(company.key, CompanyStatus.ERROR,
                                         error=f"{exc.__class__.__name__}: {exc}")
                    self.progress.errors += 1
                finally:
                    queue.task_done()

        workers = [asyncio.create_task(worker())
                   for _ in range(min(self.concurrency, max(1, queue.qsize())))]
        await asyncio.gather(*workers, return_exceptions=True)

    # ------------------------------------------------------------------ #

    async def process_company(self, company: Company,
                              connectors: list[BaseConnector]) -> None:
        """Полный цикл по одной компании."""
        label = company.display_name
        self.log.info("[%s] ▶ начинаем: %s", company.key, label)
        polled: list[str] = []
        retry_later = False

        ran: set[str] = set()
        progressed = True
        while progressed and not self.stop_requested:
            progressed = False
            for connector in connectors:
                if connector.name in ran:
                    continue
                if not connector.can_run(company):
                    continue
                if not await self._source_available(connector.name):
                    continue
                await self.pause_event.wait()
                if self.stop_requested:
                    break

                result = await connector.safe_fetch(company)
                ran.add(connector.name)
                polled.append(connector.name)
                progressed = True

                if not result.ok:
                    await self._record_source_error(connector.name, result.error or "ошибка")
                    if result.retry_later:
                        retry_later = True
                    self.log.info("[%s]   %s: ошибка — %s",
                                  company.key, connector.title, result.error)
                    continue
                await self._record_source_success(connector.name)

                if result.company_updates:
                    company.apply_updates(result.company_updates)
                    self.db.save_company_fields(company)

                valid_contacts = await self._validate_contacts(company, result.contacts)
                if valid_contacts:
                    self.db.add_contacts(company.key, valid_contacts)
                self.log.info(
                    "[%s]   %s: контактов %d (валидных %d)%s",
                    company.key, connector.title,
                    len(result.contacts), len(valid_contacts),
                    f", поля: {', '.join(result.company_updates)}" if result.company_updates else "",
                )

                if self._enough(company):
                    self.log.info("[%s]   достаточно (режим %s) — дальше не ищем",
                                  company.key, self.depth)
                    progressed = False
                    break

        # --- финал: кросс-сверка, скоринг, статус --------------------------
        all_contacts = self.db.contacts_for(company.key)
        merged = merge_and_score(company, all_contacts, self.config)
        has_email = any(m.type == ContactType.EMAIL for m in merged)
        has_phone = any(m.type == ContactType.PHONE for m in merged)

        if retry_later and not (has_email and has_phone):
            status = CompanyStatus.RETRY_LATER
        else:
            status = CompanyStatus.DONE
        self.db.mark_company(company.key, status, sources_polled=polled, merged=merged)

        self.progress.processed += 1
        if has_email:
            self.progress.found_email += 1
        if has_phone:
            self.progress.found_phone += 1
        if status == CompanyStatus.RETRY_LATER:
            self.progress.errors += 1
        self.log.info("[%s] ■ готово (%s): e-mail %s, телефонов %s, источники: %s",
                      company.key, status.value,
                      sum(1 for m in merged if m.type == ContactType.EMAIL),
                      sum(1 for m in merged if m.type == ContactType.PHONE),
                      ", ".join(polled) or "—")
        self._notify(f"{label}: {'✓' if has_email or has_phone else '—'}")

    # ------------------------------------------------------------------ #

    def _enough(self, company: Company) -> bool:
        """Достигнут ли настроенный порог достаточности."""
        if self.depth != "first_email":
            return False
        contacts = self.db.contacts_for(company.key)
        return any(c.type == ContactType.EMAIL for c in contacts)

    async def _validate_contacts(self, company: Company,
                                 contacts: list[Contact]) -> list[Contact]:
        """Централизованная валидация: почта (RFC+MX+стоп-листы), телефоны."""
        out: list[Contact] = []
        site_domain = domain_of(company.any_website or "") if company.any_website else None
        for contact in contacts:
            if contact.type == ContactType.EMAIL:
                verdict = await self.email_validator.validate(
                    contact.value, company_site_domain=site_domain)
                if not verdict.valid:
                    self.log.debug("[%s]   отсев e-mail %s: %s",
                                   company.key, contact.value, verdict.reason)
                    continue
                contact.value = verdict.email
                contact.extra["is_free_mail"] = verdict.is_free_mail
                contact.extra["is_corporate"] = verdict.is_corporate
                if verdict.mx_checked:
                    contact.extra["mx_ok"] = verdict.mx_ok
                out.append(contact)
            elif contact.type == ContactType.PHONE:
                # телефоны нормализованы коннекторами; последний рубеж
                if contact.value.startswith("+7") and len(contact.value) == 12:
                    out.append(contact)
            else:
                out.append(contact)
        return out

    # ------------------------------------------------------------------ #
    # Circuit breaker по источникам                                       #
    # ------------------------------------------------------------------ #

    async def _source_available(self, source: str) -> bool:
        async with self._breaker_lock:
            state = self.db.source_state(source)
            paused_until = state.get("paused_until")
            if paused_until and time.time() < float(paused_until):
                return False
            return True

    async def _record_source_error(self, source: str, note: str) -> None:
        async with self._breaker_lock:
            state = self.db.source_state(source)
            errors = int(state.get("consecutive_errors", 0)) + 1
            paused_until = state.get("paused_until")
            if errors >= self._breaker_threshold:
                paused_until = time.time() + self._breaker_pause
                self.log.warning(
                    "Источник «%s» стабильно отдаёт ошибки (%d подряд) — пауза %.0f минут",
                    source, errors, self._breaker_pause / 60)
                errors = 0
            self.db.set_source_state(source, errors, paused_until, note=note[:300])

    async def _record_source_success(self, source: str) -> None:
        async with self._breaker_lock:
            state = self.db.source_state(source)
            if int(state.get("consecutive_errors", 0)) != 0 or state.get("paused_until"):
                self.db.set_source_state(source, 0, None)
