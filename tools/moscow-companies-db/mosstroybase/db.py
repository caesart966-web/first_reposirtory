"""Хранилище базы компаний: SQLite, дедупликация по ИНН, слияние контактов."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterator

from .normalize import merge_unique

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    inn TEXT PRIMARY KEY,
    ogrn TEXT,
    name TEXT,
    name_short TEXT,
    kind TEXT DEFAULT 'ЮЛ',
    region_code TEXT,
    address TEXT,
    okved_main TEXT,
    okved_add TEXT DEFAULT '[]',
    msp_category TEXT,
    egrul_status TEXT,
    is_active INTEGER,
    sro_member INTEGER,
    sro_info TEXT DEFAULT '[]',
    director TEXT,
    director_post TEXT,
    emails TEXT DEFAULT '[]',
    phones TEXT DEFAULT '[]',
    phones_site TEXT DEFAULT '[]',
    website TEXT,
    sources TEXT DEFAULT '[]',
    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_companies_okved_main ON companies(okved_main);
CREATE INDEX IF NOT EXISTS idx_companies_region ON companies(region_code);
"""

_LIST_FIELDS = ("okved_add", "emails", "phones", "phones_site", "sources", "sro_info")
_SCALAR_FIELDS = (
    "ogrn", "name", "name_short", "kind", "region_code", "address",
    "okved_main", "msp_category", "egrul_status", "is_active", "sro_member",
    "director", "director_post", "website",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class CompanyDB:
    def __init__(self, path: str):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Дотягивает схему старых баз до текущей (новые колонки)."""
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(companies)")}
        for column, ddl in (
            ("sro_member", "sro_member INTEGER"),
            ("sro_info", "sro_info TEXT DEFAULT '[]'"),
            ("director", "director TEXT"),
            ("director_post", "director_post TEXT"),
            ("phones_site", "phones_site TEXT DEFAULT '[]'"),
        ):
            if column not in existing:
                self.conn.execute(f"ALTER TABLE companies ADD COLUMN {ddl}")
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    def __enter__(self) -> "CompanyDB":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- запись ---------------------------------------------------------

    def upsert(self, company: dict[str, Any]) -> None:
        """Вставляет компанию или дополняет существующую запись.

        Списковые поля (контакты, ОКВЭД доп., источники) объединяются,
        скалярные — перезаписываются только непустыми новыми значениями.
        """
        inn = (company.get("inn") or "").strip()
        if not inn:
            return
        row = self.get(inn)
        now = _now()
        if row is None:
            values = {
                "inn": inn,
                "created_at": now,
                "updated_at": now,
                "kind": company.get("kind") or "ЮЛ",
            }
            for field in _SCALAR_FIELDS:
                if field in company and company[field] not in (None, ""):
                    values[field] = company[field]
            for field in _LIST_FIELDS:
                values[field] = json.dumps(
                    merge_unique(company.get(field)), ensure_ascii=False
                )
            columns = ", ".join(values)
            placeholders = ", ".join("?" for _ in values)
            self.conn.execute(
                f"INSERT INTO companies ({columns}) VALUES ({placeholders})",
                list(values.values()),
            )
        else:
            updates: dict[str, Any] = {"updated_at": now}
            for field in _SCALAR_FIELDS:
                new = company.get(field)
                if new not in (None, "") and new != row.get(field):
                    updates[field] = new
            for field in _LIST_FIELDS:
                merged = merge_unique(row.get(field), company.get(field))
                if merged != row.get(field):
                    updates[field] = json.dumps(merged, ensure_ascii=False)
            assignments = ", ".join(f"{f} = ?" for f in updates)
            self.conn.execute(
                f"UPDATE companies SET {assignments} WHERE inn = ?",
                [*updates.values(), inn],
            )
        self.conn.commit()

    def replace_list(self, inn: str, field: str, values: list[str]) -> None:
        """Полностью заменяет списковое поле компании (для чистки мусора)."""
        if field not in _LIST_FIELDS:
            raise ValueError(f"не списковое поле: {field}")
        self.conn.execute(
            f"UPDATE companies SET {field} = ?, updated_at = ? WHERE inn = ?",
            (json.dumps(merge_unique(values), ensure_ascii=False), _now(), inn),
        )
        self.conn.commit()

    # -- чтение ---------------------------------------------------------

    def get(self, inn: str) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT * FROM companies WHERE inn = ?", (inn,))
        row = cur.fetchone()
        return self._decode(row) if row else None

    def iter_all(self, where: str = "", params: tuple = ()) -> Iterator[dict[str, Any]]:
        sql = "SELECT * FROM companies"
        if where:
            sql += " WHERE " + where
        sql += " ORDER BY inn"
        for row in self.conn.execute(sql, params):
            yield self._decode(row)

    def iter_missing_source(self, source: str, limit: int = 0) -> Iterator[dict[str, Any]]:
        """Компании, ещё не обработанные указанным источником."""
        count = 0
        for company in self.iter_all():
            if source in company["sources"]:
                continue
            yield company
            count += 1
            if limit and count >= limit:
                return

    def stats(self) -> dict[str, Any]:
        def one(sql: str) -> int:
            return self.conn.execute(sql).fetchone()[0]

        return {
            "всего": one("SELECT COUNT(*) FROM companies"),
            "действующих": one("SELECT COUNT(*) FROM companies WHERE is_active = 1"),
            "ликвидированных": one("SELECT COUNT(*) FROM companies WHERE is_active = 0"),
            "с e-mail": one("SELECT COUNT(*) FROM companies WHERE emails != '[]'"),
            "с телефоном": one("SELECT COUNT(*) FROM companies WHERE phones != '[]'"),
            "с сайтом": one(
                "SELECT COUNT(*) FROM companies WHERE website IS NOT NULL AND website != ''"
            ),
            "отсекаются (в СРО/исключены < года)": one(
                "SELECT COUNT(*) FROM companies WHERE sro_member = 1"
            ),
            "стройка (41–43)": one(
                "SELECT COUNT(*) FROM companies WHERE okved_main LIKE '41%' "
                "OR okved_main LIKE '42%' OR okved_main LIKE '43%'"
            ),
            "проект/изыскания (71.1x)": one(
                "SELECT COUNT(*) FROM companies WHERE okved_main LIKE '71.1%'"
            ),
            "категория «среднее»": one(
                "SELECT COUNT(*) FROM companies WHERE msp_category = 'среднее'"
            ),
            "категория «малое»": one(
                "SELECT COUNT(*) FROM companies WHERE msp_category = 'малое'"
            ),
            "категория «микро»": one(
                "SELECT COUNT(*) FROM companies WHERE msp_category = 'микро'"
            ),
        }

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        company = dict(row)
        for field in _LIST_FIELDS:
            try:
                company[field] = json.loads(company.get(field) or "[]")
            except (TypeError, ValueError):
                company[field] = []
        return company
