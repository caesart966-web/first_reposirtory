"""SQLite-хранилище: рабочая база, кэш ответов с TTL, возобновление после сбоя.

Все промежуточные результаты пишутся сюда сразу (не копятся в памяти), поэтому
принудительная остановка на любой компании не теряет данные: повторный запуск
продолжает с первой компании в статусе pending/retry_later.

Потокобезопасность: одно соединение + RLock (GUI запускает пайплайн в отдельном
потоке). Операции короткие, WAL-режим не даёт писателям блокировать читателей.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from core.models import (
    Company,
    CompanyStatus,
    Contact,
    MergedContact,
    dumps,
    now_iso,
)
import json

_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    key                TEXT PRIMARY KEY,
    inn                TEXT,
    ogrn               TEXT,
    name_full          TEXT,
    name_short         TEXT,
    entity_status      TEXT,
    reg_date           TEXT,
    okved              TEXT,
    region             TEXT,
    address            TEXT,
    director_name      TEXT,
    director_position  TEXT,
    website            TEXT,
    website_verified   INTEGER NOT NULL DEFAULT 0,
    website_candidate  TEXT,
    raw_json           TEXT,
    status             TEXT NOT NULL DEFAULT 'pending',
    sources_polled     TEXT,
    merged_json        TEXT,
    error              TEXT,
    processed_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_companies_status ON companies(status);

CREATE TABLE IF NOT EXISTS contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_key TEXT NOT NULL,
    type        TEXT NOT NULL,
    value       TEXT NOT NULL,
    raw         TEXT,
    source      TEXT NOT NULL,
    source_url  TEXT,
    level       TEXT,
    confidence  INTEGER NOT NULL DEFAULT 0,
    is_primary  INTEGER NOT NULL DEFAULT 0,
    extra_json  TEXT,
    collected_at TEXT,
    UNIQUE(company_key, type, value, source)
);
CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_key);

CREATE TABLE IF NOT EXISTS http_cache (
    cache_key    TEXT PRIMARY KEY,
    url          TEXT,
    status       INTEGER,
    body         BLOB,
    content_type TEXT,
    fetched_at   REAL
);

CREATE TABLE IF NOT EXISTS source_state (
    source             TEXT PRIMARY KEY,
    consecutive_errors INTEGER NOT NULL DEFAULT 0,
    paused_until       REAL,
    unavailable        INTEGER NOT NULL DEFAULT 0,
    note               TEXT
);
"""


class Database:
    """Обёртка над SQLite со всеми запросами приложения."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript("PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.commit()
            self._conn.close()

    # ------------------------------------------------------------------ #
    # Компании (очередь и результаты)                                     #
    # ------------------------------------------------------------------ #

    def upsert_company_input(self, company: Company) -> bool:
        """Добавить компанию из входного файла. Возвращает True, если новая.

        Уже обработанные (done) компании не сбрасываются — так работает резюме.
        """
        with self._lock:
            cur = self._conn.execute(
                "SELECT status FROM companies WHERE key = ?", (company.key,)
            )
            row = cur.fetchone()
            if row is None:
                self._conn.execute(
                    """INSERT INTO companies
                       (key, inn, ogrn, name_full, name_short, region, website, raw_json, status)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        company.key, company.inn, company.ogrn, company.name_full,
                        company.name_short, company.region, company.website,
                        dumps(company.raw), CompanyStatus.PENDING.value,
                    ),
                )
                self._conn.commit()
                return True
            return False

    def reset_all_pending(self) -> None:
        """Полный пересбор: сбросить статусы всех компаний (--fresh)."""
        with self._lock:
            self._conn.execute(
                "UPDATE companies SET status=?, error=NULL, sources_polled=NULL, merged_json=NULL",
                (CompanyStatus.PENDING.value,),
            )
            self._conn.execute("DELETE FROM contacts")
            self._conn.commit()

    def fetch_companies(self, statuses: Iterable[CompanyStatus]) -> list[Company]:
        values = [s.value for s in statuses]
        placeholders = ",".join("?" * len(values))
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM companies WHERE status IN ({placeholders}) ORDER BY rowid",
                values,
            ).fetchall()
        return [self._row_to_company(r) for r in rows]

    def fetch_all_companies(self) -> list[Company]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM companies ORDER BY rowid").fetchall()
        return [self._row_to_company(r) for r in rows]

    def company_row(self, key: str) -> Optional[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM companies WHERE key=?", (key,)
            ).fetchone()

    @staticmethod
    def _row_to_company(row: sqlite3.Row) -> Company:
        raw = {}
        if row["raw_json"]:
            try:
                raw = json.loads(row["raw_json"])
            except (ValueError, TypeError):
                raw = {}
        return Company(
            key=row["key"], inn=row["inn"], ogrn=row["ogrn"],
            name_full=row["name_full"], name_short=row["name_short"],
            entity_status=row["entity_status"], reg_date=row["reg_date"],
            okved=row["okved"], region=row["region"], address=row["address"],
            director_name=row["director_name"], director_position=row["director_position"],
            website=row["website"], website_verified=bool(row["website_verified"]),
            website_candidate=row["website_candidate"], raw=raw,
        )

    def save_company_fields(self, company: Company) -> None:
        """Сохранить обогащённые поля компании (после каждого коннектора)."""
        with self._lock:
            self._conn.execute(
                """UPDATE companies SET inn=?, ogrn=?, name_full=?, name_short=?,
                   entity_status=?, reg_date=?, okved=?, region=?, address=?,
                   director_name=?, director_position=?, website=?,
                   website_verified=?, website_candidate=? WHERE key=?""",
                (
                    company.inn, company.ogrn, company.name_full, company.name_short,
                    company.entity_status, company.reg_date, company.okved,
                    company.region, company.address, company.director_name,
                    company.director_position, company.website,
                    int(company.website_verified), company.website_candidate,
                    company.key,
                ),
            )
            self._conn.commit()

    def mark_company(self, key: str, status: CompanyStatus,
                     sources_polled: Optional[list[str]] = None,
                     error: Optional[str] = None,
                     merged: Optional[list[MergedContact]] = None) -> None:
        with self._lock:
            self._conn.execute(
                """UPDATE companies SET status=?, sources_polled=?, error=?,
                   merged_json=COALESCE(?, merged_json), processed_at=? WHERE key=?""",
                (
                    status.value,
                    dumps(sources_polled) if sources_polled is not None else None,
                    error,
                    dumps([m.to_dict() for m in merged]) if merged is not None else None,
                    now_iso(),
                    key,
                ),
            )
            self._conn.commit()

    def merged_contacts(self, key: str) -> list[MergedContact]:
        row = self.company_row(key)
        if not row or not row["merged_json"]:
            return []
        try:
            data = json.loads(row["merged_json"])
            return [MergedContact.from_dict(d) for d in data]
        except (ValueError, TypeError, KeyError):
            return []

    def status_counts(self) -> dict[str, int]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT status, COUNT(*) AS n FROM companies GROUP BY status"
            ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    # ------------------------------------------------------------------ #
    # Контакты (сырые, по источникам)                                     #
    # ------------------------------------------------------------------ #

    def add_contacts(self, company_key: str, contacts: Iterable[Contact]) -> None:
        with self._lock:
            for c in contacts:
                self._conn.execute(
                    """INSERT INTO contacts
                       (company_key, type, value, raw, source, source_url, level,
                        confidence, is_primary, extra_json, collected_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(company_key, type, value, source) DO UPDATE SET
                         source_url=excluded.source_url,
                         raw=excluded.raw,
                         extra_json=excluded.extra_json""",
                    (
                        company_key, c.type.value, c.value, c.raw, c.source,
                        c.source_url, c.level.value, c.confidence,
                        int(c.is_primary), dumps(c.extra), c.collected_at,
                    ),
                )
            self._conn.commit()

    def contacts_for(self, company_key: str) -> list[Contact]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM contacts WHERE company_key=? ORDER BY id", (company_key,)
            ).fetchall()
        out: list[Contact] = []
        for r in rows:
            extra = {}
            if r["extra_json"]:
                try:
                    extra = json.loads(r["extra_json"])
                except (ValueError, TypeError):
                    extra = {}
            out.append(Contact.from_dict({
                "type": r["type"], "value": r["value"], "raw": r["raw"] or "",
                "source": r["source"], "source_url": r["source_url"],
                "level": r["level"] or "D", "confidence": r["confidence"],
                "is_primary": bool(r["is_primary"]), "extra": extra,
                "collected_at": r["collected_at"],
            }))
        return out

    # ------------------------------------------------------------------ #
    # HTTP-кэш с TTL                                                      #
    # ------------------------------------------------------------------ #

    def cache_get(self, cache_key: str, ttl_seconds: int) -> Optional[sqlite3.Row]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM http_cache WHERE cache_key=?", (cache_key,)
            ).fetchone()
        if row is None:
            return None
        if time.time() - float(row["fetched_at"]) > ttl_seconds:
            with self._lock:
                self._conn.execute("DELETE FROM http_cache WHERE cache_key=?", (cache_key,))
                self._conn.commit()
            return None
        return row

    def cache_put(self, cache_key: str, url: str, status: int,
                  body: bytes, content_type: str) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO http_cache (cache_key, url, status, body, content_type, fetched_at)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(cache_key) DO UPDATE SET
                     status=excluded.status, body=excluded.body,
                     content_type=excluded.content_type, fetched_at=excluded.fetched_at""",
                (cache_key, url, status, body, content_type, time.time()),
            )
            self._conn.commit()

    def cache_purge_expired(self, ttl_seconds: int) -> int:
        deadline = time.time() - ttl_seconds
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM http_cache WHERE fetched_at < ?", (deadline,)
            )
            self._conn.commit()
            return cur.rowcount

    # ------------------------------------------------------------------ #
    # Состояние источников (circuit breaker, недоступность)               #
    # ------------------------------------------------------------------ #

    def source_state(self, source: str) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM source_state WHERE source=?", (source,)
            ).fetchone()
        if row is None:
            return {"source": source, "consecutive_errors": 0,
                    "paused_until": None, "unavailable": False, "note": None}
        return {
            "source": row["source"],
            "consecutive_errors": row["consecutive_errors"],
            "paused_until": row["paused_until"],
            "unavailable": bool(row["unavailable"]),
            "note": row["note"],
        }

    def set_source_state(self, source: str, consecutive_errors: int,
                         paused_until: Optional[float],
                         unavailable: bool = False, note: Optional[str] = None) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO source_state (source, consecutive_errors, paused_until, unavailable, note)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(source) DO UPDATE SET
                     consecutive_errors=excluded.consecutive_errors,
                     paused_until=excluded.paused_until,
                     unavailable=excluded.unavailable,
                     note=excluded.note""",
                (source, consecutive_errors, paused_until, int(unavailable), note),
            )
            self._conn.commit()

    def unavailable_sources(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM source_state WHERE unavailable=1"
            ).fetchall()
        return [dict(r) for r in rows]
