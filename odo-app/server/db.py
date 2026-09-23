"""SQLite без ORM: компании, договоры, файлы, письма, журнал."""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, inn TEXT, kpp TEXT, sro_name TEXT, odo_level INTEGER, vv_level INTEGER,
  notes TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contracts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  number TEXT, card TEXT, assessment TEXT, draft_meta TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  decision TEXT, decision_note TEXT, decided_by TEXT, decided_at TEXT, case_id TEXT,
  sro_notified INTEGER DEFAULT 0, sro_notified_date TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
  filename TEXT NOT NULL, stored_path TEXT NOT NULL, kind TEXT, text_chars INTEGER, scanned INTEGER DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS letters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
  letter_text TEXT, objection TEXT, analysis TEXT, reply_md TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, user TEXT, action TEXT NOT NULL, contract_id INTEGER, details TEXT
);
"""


def now() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init():
    with connect() as con:
        con.executescript(SCHEMA)


@contextmanager
def tx():
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


def j(row, key):
    """JSON-поле строки → объект (или None)."""
    v = row[key] if row is not None else None
    return json.loads(v) if v else None


# ---- компании ----------------------------------------------------------
def companies():
    with tx() as con:
        return [dict(r) for r in con.execute("SELECT * FROM companies ORDER BY name")]


def company(cid: int):
    with tx() as con:
        r = con.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
        return dict(r) if r else None


def company_by_inn(inn: str):
    if not inn:
        return None
    with tx() as con:
        r = con.execute("SELECT * FROM companies WHERE inn=?", (inn,)).fetchone()
        return dict(r) if r else None


def add_company(name, inn=None, kpp=None, sro_name=None, odo_level=None, vv_level=None, notes=None) -> int:
    with tx() as con:
        cur = con.execute("INSERT INTO companies(name,inn,kpp,sro_name,odo_level,vv_level,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",
                          (name, inn or None, kpp or None, sro_name or None, odo_level, vv_level, notes or None, now()))
        return cur.lastrowid


def update_company(cid, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    with tx() as con:
        con.execute(f"UPDATE companies SET {cols} WHERE id=?", (*fields.values(), cid))


def delete_company(cid):
    with tx() as con:
        con.execute("DELETE FROM companies WHERE id=?", (cid,))


# ---- договоры ----------------------------------------------------------
def contracts_of(cid: int):
    with tx() as con:
        rows = con.execute("SELECT * FROM contracts WHERE company_id=? ORDER BY id", (cid,)).fetchall()
        return [_contract_row(r) for r in rows]


def _contract_row(r):
    d = dict(r)
    d["card"] = json.loads(d["card"]) if d.get("card") else None
    d["assessment"] = json.loads(d["assessment"]) if d.get("assessment") else None
    d["draft_meta"] = json.loads(d["draft_meta"]) if d.get("draft_meta") else None
    return d


def contract(cid: int):
    with tx() as con:
        r = con.execute("SELECT * FROM contracts WHERE id=?", (cid,)).fetchone()
        return _contract_row(r) if r else None


def add_contract(company_id, number, card, draft_meta) -> int:
    with tx() as con:
        cur = con.execute("INSERT INTO contracts(company_id,number,card,draft_meta,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                          (company_id, number, json.dumps(card, ensure_ascii=False), json.dumps(draft_meta, ensure_ascii=False), "draft", now(), now()))
        return cur.lastrowid


def update_contract(cid, **fields):
    for k in ("card", "assessment", "draft_meta"):
        if k in fields and fields[k] is not None and not isinstance(fields[k], str):
            fields[k] = json.dumps(fields[k], ensure_ascii=False)
    fields["updated_at"] = now()
    cols = ", ".join(f"{k}=?" for k in fields)
    with tx() as con:
        con.execute(f"UPDATE contracts SET {cols} WHERE id=?", (*fields.values(), cid))


def delete_contract(cid):
    with tx() as con:
        con.execute("DELETE FROM contracts WHERE id=?", (cid,))


def find_contract_by_number(company_id, number):
    if not number:
        return None
    with tx() as con:
        r = con.execute("SELECT * FROM contracts WHERE company_id=? AND number=?", (company_id, number)).fetchone()
        return _contract_row(r) if r else None


# ---- файлы -------------------------------------------------------------
def add_file(contract_id, filename, stored_path, kind, text_chars, scanned) -> int:
    with tx() as con:
        cur = con.execute("INSERT INTO files(contract_id,filename,stored_path,kind,text_chars,scanned,created_at) VALUES(?,?,?,?,?,?,?)",
                          (contract_id, filename, stored_path, kind, text_chars, 1 if scanned else 0, now()))
        return cur.lastrowid


def files_of(contract_id):
    with tx() as con:
        return [dict(r) for r in con.execute("SELECT * FROM files WHERE contract_id=? ORDER BY id", (contract_id,))]


def file(fid):
    with tx() as con:
        r = con.execute("SELECT * FROM files WHERE id=?", (fid,)).fetchone()
        return dict(r) if r else None


# ---- письма ------------------------------------------------------------
def add_letter(contract_id, letter_text, objection, analysis, reply_md) -> int:
    with tx() as con:
        cur = con.execute("INSERT INTO letters(contract_id,letter_text,objection,analysis,reply_md,created_at) VALUES(?,?,?,?,?,?)",
                          (contract_id, letter_text, json.dumps(objection, ensure_ascii=False), json.dumps(analysis, ensure_ascii=False), reply_md, now()))
        return cur.lastrowid


def letters_of(contract_id):
    with tx() as con:
        out = []
        for r in con.execute("SELECT * FROM letters WHERE contract_id=? ORDER BY id DESC", (contract_id,)):
            d = dict(r)
            d["objection"] = json.loads(d["objection"]) if d["objection"] else None
            d["analysis"] = json.loads(d["analysis"]) if d["analysis"] else None
            out.append(d)
        return out


def letter(lid):
    with tx() as con:
        r = con.execute("SELECT * FROM letters WHERE id=?", (lid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["objection"] = json.loads(d["objection"]) if d["objection"] else None
        d["analysis"] = json.loads(d["analysis"]) if d["analysis"] else None
        return d


# ---- журнал ------------------------------------------------------------
def log(user, action, contract_id=None, details=None):
    with tx() as con:
        con.execute("INSERT INTO log(ts,user,action,contract_id,details) VALUES(?,?,?,?,?)", (now(), user, action, contract_id, details))


def log_tail(limit=200):
    with tx() as con:
        return [dict(r) for r in con.execute("SELECT * FROM log ORDER BY id DESC LIMIT ?", (limit,))]
