"""Хранилище проекта на SQLite (generic document store).

Каждая сущность модели данных хранится строкой в `entities`: id/type/project_id —
в колонках для быстрых выборок, полное тело — в JSON. Это MVP-выбор: гибко под
схемы и легко мигрирует на Postgres/JSONB. Также: text_chunks (поиск), review_log
(правки человека), review_requests (очередь HITL).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from . import config
from .ids import new_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    id         TEXT PRIMARY KEY,
    type       TEXT NOT NULL,
    project_id TEXT,
    data       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entities_type_proj ON entities(type, project_id);

CREATE TABLE IF NOT EXISTS text_chunks (
    id            TEXT PRIMARY KEY,
    project_id    TEXT,
    document_id   TEXT,
    document_type TEXT,
    locator       TEXT,
    page          INTEGER,
    text          TEXT NOT NULL,
    embedding     TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_proj ON text_chunks(project_id, document_type);

CREATE TABLE IF NOT EXISTS review_requests (
    id                TEXT PRIMARY KEY,
    project_id        TEXT,
    entity_type       TEXT NOT NULL,
    entity_id         TEXT NOT NULL,
    reason            TEXT,
    severity          TEXT,
    suggested_options TEXT,
    status            TEXT NOT NULL,
    created_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_log (
    id           TEXT PRIMARY KEY,
    entity_type  TEXT, entity_id TEXT, field TEXT,
    system_value TEXT, human_value TEXT,
    action       TEXT, actor TEXT, reason TEXT, at TEXT
);
"""


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = str(path or config.DB_PATH)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ----- entities -----
    def upsert(self, obj: dict) -> dict:
        obj = dict(obj)
        etype = obj.get("type")
        if not etype:
            raise ValueError("entity requires 'type'")
        if not obj.get("id"):
            obj["id"] = new_id(etype)
        now = _now()
        row = self.conn.execute("SELECT created_at FROM entities WHERE id=?", (obj["id"],)).fetchone()
        created = row["created_at"] if row else now
        self.conn.execute(
            "INSERT INTO entities(id,type,project_id,data,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "type=excluded.type, project_id=excluded.project_id, "
            "data=excluded.data, updated_at=excluded.updated_at",
            (obj["id"], etype, obj.get("project_id"), json.dumps(obj, ensure_ascii=False), created, now),
        )
        self.conn.commit()
        return obj

    def get(self, entity_id: str) -> dict | None:
        row = self.conn.execute("SELECT data FROM entities WHERE id=?", (entity_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def query(self, entity_type: str | None = None, project_id: str | None = None,
              predicate=None) -> list[dict]:
        sql, params = "SELECT data FROM entities WHERE 1=1", []
        if entity_type:
            sql += " AND type=?"; params.append(entity_type)
        if project_id:
            sql += " AND project_id=?"; params.append(project_id)
        rows = self.conn.execute(sql, params).fetchall()
        out = [json.loads(r["data"]) for r in rows]
        if predicate:
            out = [o for o in out if predicate(o)]
        return out

    def delete(self, entity_id: str) -> None:
        self.conn.execute("DELETE FROM entities WHERE id=?", (entity_id,))
        self.conn.commit()

    # ----- text chunks (поиск) -----
    def add_chunk(self, text: str, *, project_id=None, document_id=None,
                  document_type=None, locator=None, page=None, embedding=None) -> str:
        cid = new_id("TextChunk")
        self.conn.execute(
            "INSERT INTO text_chunks(id,project_id,document_id,document_type,locator,page,text,embedding)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (cid, project_id, document_id, document_type, locator, page, text,
             json.dumps(embedding) if embedding is not None else None),
        )
        self.conn.commit()
        return cid

    def chunks(self, project_id: str | None = None,
               document_type: str | None = None) -> list[dict]:
        sql, params = "SELECT * FROM text_chunks WHERE 1=1", []
        if project_id:
            sql += " AND project_id=?"; params.append(project_id)
        if document_type:
            sql += " AND document_type=?"; params.append(document_type)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    # ----- human-in-the-loop -----
    def add_review_request(self, *, entity_type, entity_id, reason, severity,
                           suggested_options=None, project_id=None) -> dict:
        rid = new_id("ReviewRequest")
        rec = {
            "id": rid, "project_id": project_id, "entity_type": entity_type,
            "entity_id": entity_id, "reason": reason, "severity": severity,
            "suggested_options": suggested_options or [], "status": "queued",
            "created_at": _now(),
        }
        self.conn.execute(
            "INSERT INTO review_requests(id,project_id,entity_type,entity_id,reason,severity,"
            "suggested_options,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (rid, project_id, entity_type, entity_id, reason, severity,
             json.dumps(rec["suggested_options"], ensure_ascii=False), "queued", rec["created_at"]),
        )
        self.conn.commit()
        return rec

    def add_review_log(self, *, entity_type, entity_id, field, system_value,
                       human_value, action, actor, reason=None) -> None:
        self.conn.execute(
            "INSERT INTO review_log(id,entity_type,entity_id,field,system_value,human_value,"
            "action,actor,reason,at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (new_id("ReviewLog"), entity_type, entity_id, field,
             json.dumps(system_value, ensure_ascii=False), json.dumps(human_value, ensure_ascii=False),
             action, actor, reason, _now()),
        )
        self.conn.commit()


_default: Database | None = None


def get_db() -> Database:
    """Синглтон-подключение для MCP-сервера."""
    global _default
    if _default is None:
        config.ensure_dirs()
        _default = Database()
    return _default
