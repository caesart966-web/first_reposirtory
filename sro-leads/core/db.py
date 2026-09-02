"""SQLite: схема и доступ. ИНН везде строкой."""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional

from .models import Org, RegistryRow, Signal, SnapshotMeta
from .utils import now_str

SCHEMA = """
CREATE TABLE IF NOT EXISTS orgs (
    inn TEXT PRIMARY KEY,
    ogrn TEXT,
    name TEXT,
    region TEXT,
    address TEXT,
    okved TEXT,
    site TEXT,
    phone TEXT,
    email TEXT,
    director TEXT,
    status TEXT,
    site_verified TEXT,
    phone_unverified TEXT,
    email_unverified TEXT,
    enriched_at TEXT,
    score REAL,
    priority INTEGER,
    score_updated_at TEXT
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inn TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    signal_date TEXT NOT NULL,
    source TEXT,
    url TEXT,
    raw_json TEXT,
    created_at TEXT,
    detected_by TEXT,
    UNIQUE(inn, signal_type, signal_date)
);
CREATE INDEX IF NOT EXISTS idx_signals_inn ON signals(inn);

CREATE TABLE IF NOT EXISTS registry_snapshots (
    snapshot_date TEXT NOT NULL,
    source TEXT NOT NULL,
    inn TEXT NOT NULL,
    sro_name TEXT NOT NULL,
    reg_number TEXT,
    status TEXT,
    name TEXT,
    url TEXT,
    status_code TEXT,
    status_date TEXT,
    reg_date TEXT,
    PRIMARY KEY (snapshot_date, source, inn, sro_name)
);
CREATE INDEX IF NOT EXISTS idx_snap_src_date ON registry_snapshots(source, snapshot_date);

CREATE TABLE IF NOT EXISTS snapshot_meta (
    snapshot_date TEXT NOT NULL,
    source TEXT NOT NULL,
    declared_total INTEGER,
    fetched_rows INTEGER,
    pages_done INTEGER,
    is_partial INTEGER DEFAULT 0,
    created_at TEXT,
    PRIMARY KEY (snapshot_date, source)
);

CREATE TABLE IF NOT EXISTS outreach (
    inn TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'new',
    first_contact_at TEXT,
    note TEXT
);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    # Колонки, добавленные после первой версии схемы: базы, созданные раньше, дополняются на ходу.
    MIGRATIONS = (
        ("registry_snapshots", "status_code", "TEXT"),
        ("registry_snapshots", "status_date", "TEXT"),
        ("registry_snapshots", "reg_date", "TEXT"),
        ("signals", "detected_by", "TEXT"),
        ("orgs", "site_verified", "TEXT"),
        ("orgs", "phone_unverified", "TEXT"),
        ("orgs", "email_unverified", "TEXT"),
    )

    def _migrate(self) -> None:
        for table, column, ctype in self.MIGRATIONS:
            cols = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})").fetchall()}
            if column not in cols:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ctype}")

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------ orgs
    def ensure_org(self, inn: str, name: Optional[str] = None) -> None:
        self.conn.execute("INSERT OR IGNORE INTO orgs(inn) VALUES (?)", (inn,))
        if name:
            self.conn.execute("UPDATE orgs SET name = COALESCE(name, ?) WHERE inn = ?", (name, inn))

    def get_org(self, inn: str) -> Optional[Org]:
        row = self.conn.execute("SELECT * FROM orgs WHERE inn = ?", (inn,)).fetchone()
        if not row:
            return None
        return Org(**{k: row[k] for k in Org.__dataclass_fields__ if k in row.keys()})

    def upsert_org(self, org: Org) -> None:
        """Записывает непустые поля организации, пустые не затирает."""
        self.ensure_org(org.inn)
        fields = {k: v for k, v in org.to_row().items() if k != "inn" and v is not None}
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE orgs SET {sets} WHERE inn = ?", (*fields.values(), org.inn))

    def set_score(self, inn: str, score: float, priority: int) -> None:
        self.ensure_org(inn)
        self.conn.execute(
            "UPDATE orgs SET score = ?, priority = ?, score_updated_at = ? WHERE inn = ?",
            (score, priority, now_str(), inn),
        )

    def orgs_rows(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM orgs").fetchall()

    # --------------------------------------------------------------- signals
    def add_signals(self, signals: Iterable[Signal]) -> int:
        """Пишет сигналы, дубли (inn, type, date) молча пропускает. Возвращает число новых."""
        added = 0
        for s in signals:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO signals(inn, signal_type, signal_date, source, url, raw_json, created_at, detected_by) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (s.inn, s.signal_type, s.signal_date, s.source, s.url, s.raw_json(), now_str(), s.detected_by),
            )
            if cur.rowcount:
                added += 1
                self.ensure_org(s.inn, s.raw.get("name") if isinstance(s.raw, dict) else None)
        return added

    def signals_by_inn(self, inns: Optional[Iterable[str]] = None) -> dict[str, list[sqlite3.Row]]:
        out: dict[str, list[sqlite3.Row]] = defaultdict(list)
        if inns is None:
            rows = self.conn.execute("SELECT * FROM signals ORDER BY signal_date DESC, id DESC").fetchall()
        else:
            inns = list(inns)
            rows = []
            for i in range(0, len(inns), 500):
                chunk = inns[i : i + 500]
                q = ",".join("?" * len(chunk))
                rows += self.conn.execute(
                    f"SELECT * FROM signals WHERE inn IN ({q}) ORDER BY signal_date DESC, id DESC", chunk
                ).fetchall()
        for r in rows:
            out[r["inn"]].append(r)
        return out

    def all_signal_rows(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM signals ORDER BY signal_date DESC, id DESC"
        ).fetchall()

    # ------------------------------------------------------------- snapshots
    def has_snapshot(self, source: str, snapshot_date: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM registry_snapshots WHERE source = ? AND snapshot_date = ? LIMIT 1",
            (source, snapshot_date),
        ).fetchone()
        return row is not None

    def latest_snapshot_date(self, source: str, before: Optional[str] = None) -> Optional[str]:
        if before:
            row = self.conn.execute(
                "SELECT MAX(snapshot_date) AS d FROM registry_snapshots WHERE source = ? AND snapshot_date < ?",
                (source, before),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT MAX(snapshot_date) AS d FROM registry_snapshots WHERE source = ?", (source,)
            ).fetchone()
        return row["d"] if row and row["d"] else None

    def snapshot_rows(self, source: str, snapshot_date: str) -> list[RegistryRow]:
        rows = self.conn.execute(
            "SELECT inn, sro_name, reg_number, status, name, url, status_code, status_date, reg_date "
            "FROM registry_snapshots WHERE source = ? AND snapshot_date = ?",
            (source, snapshot_date),
        ).fetchall()
        return [RegistryRow(**dict(r)) for r in rows]

    def snapshot_size(self, source: str, snapshot_date: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM registry_snapshots WHERE source = ? AND snapshot_date = ?",
            (source, snapshot_date),
        ).fetchone()
        return int(row["n"])

    def write_snapshot(self, source: str, snapshot_date: str, rows: Iterable[RegistryRow]) -> int:
        n = 0
        for r in rows:
            self.conn.execute(
                "INSERT OR REPLACE INTO registry_snapshots"
                "(snapshot_date, source, inn, sro_name, reg_number, status, name, url, status_code, status_date, reg_date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (snapshot_date, source, r.inn, r.sro_name, r.reg_number, r.status, r.name, r.url,
                 r.status_code, r.status_date, r.reg_date),
            )
            n += 1
        return n

    def write_snapshot_meta(self, source: str, snapshot_date: str, meta: SnapshotMeta) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO snapshot_meta"
            "(snapshot_date, source, declared_total, fetched_rows, pages_done, is_partial, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (snapshot_date, source, meta.declared_total, meta.fetched_rows, meta.pages_done,
             1 if meta.is_partial else 0, now_str()),
        )

    def snapshot_meta(self, source: str, snapshot_date: str) -> Optional[SnapshotMeta]:
        row = self.conn.execute(
            "SELECT * FROM snapshot_meta WHERE source = ? AND snapshot_date = ?", (source, snapshot_date)
        ).fetchone()
        if not row:
            return None
        return SnapshotMeta(declared_total=row["declared_total"], fetched_rows=row["fetched_rows"] or 0,
                            pages_done=row["pages_done"] or 0, is_partial=bool(row["is_partial"]))

    def is_snapshot_partial(self, source: str, snapshot_date: str) -> bool:
        meta = self.snapshot_meta(source, snapshot_date)
        return bool(meta and meta.is_partial)

    def drop_snapshot(self, source: str, snapshot_date: str) -> int:
        """Удаляет снапшот за дату (строки и метаданные), чтобы снять его заново."""
        n = self.conn.execute(
            "DELETE FROM registry_snapshots WHERE source = ? AND snapshot_date = ?", (source, snapshot_date)
        ).rowcount
        self.conn.execute(
            "DELETE FROM snapshot_meta WHERE source = ? AND snapshot_date = ?", (source, snapshot_date))
        return n

    def snapshot_dates(self, source: str) -> list[str]:
        return [r["snapshot_date"] for r in self.conn.execute(
            "SELECT DISTINCT snapshot_date FROM registry_snapshots WHERE source = ? ORDER BY snapshot_date DESC",
            (source,)).fetchall()]

    def prune_snapshots(self, source: str, keep_dates: int) -> int:
        """Оставляет последние keep_dates дат по источнику, остальные удаляет."""
        dates = [
            r["snapshot_date"]
            for r in self.conn.execute(
                "SELECT DISTINCT snapshot_date FROM registry_snapshots WHERE source = ? ORDER BY snapshot_date DESC",
                (source,),
            ).fetchall()
        ]
        old = dates[keep_dates:]
        removed = 0
        for d in old:
            removed += self.drop_snapshot(source, d)
        return removed

    # -------------------------------------------------------------- outreach
    def ensure_outreach(self, inn: str) -> None:
        self.conn.execute("INSERT OR IGNORE INTO outreach(inn, status) VALUES (?, 'new')", (inn,))

    def outreach_map(self) -> dict[str, sqlite3.Row]:
        return {r["inn"]: r for r in self.conn.execute("SELECT * FROM outreach").fetchall()}

    def set_outreach(self, inn: str, status: str, note: Optional[str] = None) -> None:
        self.ensure_outreach(inn)
        self.conn.execute(
            "UPDATE outreach SET status = ?, note = COALESCE(?, note), "
            "first_contact_at = CASE WHEN status = 'new' AND ? != 'new' THEN COALESCE(first_contact_at, ?) "
            "ELSE first_contact_at END WHERE inn = ?",
            (status, note, status, now_str(), inn),
        )

    # ------------------------------------------------------------------ misc
    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def stats(self) -> dict[str, Any]:
        q = lambda sql: self.conn.execute(sql).fetchone()[0]  # noqa: E731
        return {
            "orgs": q("SELECT COUNT(*) FROM orgs"),
            "signals": q("SELECT COUNT(*) FROM signals"),
            "snapshot_rows": q("SELECT COUNT(*) FROM registry_snapshots"),
            "outreach": q("SELECT COUNT(*) FROM outreach"),
        }
