#!/usr/bin/env python3
"""Валидация реестра по JSON Schema (schemas/register.schema.json).

    python3 validate.py register.json
    python3 validate.py register.json --schema register

Требуется пакет jsonschema (pip install jsonschema). Без него — базовая
проверка обязательных полей и ссылок между сущностями.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas")


def load_json(path):
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_refs(reg: dict) -> list[str]:
    """Ссылочная целостность: каждая *_id указывает на существующую сущность."""
    errs = []
    objs = {o["id"] for o in reg.get("objects", [])}
    ctrs = {c["id"] for c in reg.get("contracts", [])}
    docs = {d["id"] for d in reg.get("documents", [])}
    for c in reg.get("contracts", []):
        if c.get("object_id") and c["object_id"] not in objs:
            errs.append(f"{c['id']}: object_id {c['object_id']} не найден")
        src = c.get("source") or {}
        if src.get("document_id") and src["document_id"] not in docs:
            errs.append(f"{c['id']}: source.document_id {src['document_id']} не найден")
    for d in reg.get("documents", []):
        if d.get("contract_id") and d["contract_id"] not in ctrs:
            errs.append(f"{d['id']}: contract_id {d['contract_id']} не найден")
    seen = set()
    for li in reg.get("line_items", []):
        if li["id"] in seen:
            errs.append(f"{li['id']}: дубль идентификатора")
        seen.add(li["id"])
        if li["document_id"] not in docs:
            errs.append(f"{li['id']}: document_id {li['document_id']} не найден")
        if li.get("contract_id") and li["contract_id"] not in ctrs:
            errs.append(f"{li['id']}: contract_id {li['contract_id']} не найден")
        if li.get("object_id") and li["object_id"] not in objs:
            errs.append(f"{li['id']}: object_id {li['object_id']} не найден")
        if li.get("amount_rub") is None and li.get("amount_with_vat_rub") is None and not li.get("is_summary"):
            errs.append(f"{li['id']}: нет ни одной суммы")
    return errs


def check_sums(reg: dict) -> list[str]:
    """Контроль: сумма строк документа против его итога (допуск 1 ₽ + 0,01 %)."""
    warns = []
    from collections import defaultdict
    by_doc = defaultdict(lambda: [0.0, 0.0, 0, False])
    for li in reg.get("line_items", []):
        if li.get("is_summary"):
            continue
        b = by_doc[li["document_id"]]
        b[2] += 1
        if li.get("amount_rub") is not None:
            b[0] += float(li["amount_rub"])
        if li.get("amount_with_vat_rub") is not None:
            b[1] += float(li["amount_with_vat_rub"])
    for d in reg.get("documents", []):
        b = by_doc.get(d["id"])
        if not b or b[2] == 0:
            continue
        for key, idx in (("amount_without_vat_rub", 0), ("amount_with_vat_rub", 1)):
            tot = d.get(key)
            if tot is None or b[idx] == 0:
                continue
            tol = 1.0 + abs(float(tot)) * 0.0001
            if abs(float(tot) - b[idx]) > tol:
                warns.append(f"{d['id']} ({d['kind']} № {d['number']}): строки {key} = {b[idx]:,.2f}, итог документа {float(tot):,.2f}")
    return warns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("data")
    ap.add_argument("--schema", default="register")
    args = ap.parse_args(argv)
    schema_path = os.path.join(SCHEMA_DIR, f"{args.schema}.schema.json")
    schema = load_json(schema_path)
    data = load_json(args.data)
    rc = 0
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
        v = Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        errors = sorted(v.iter_errors(data), key=lambda e: list(e.path))
        for e in errors:
            loc = "/".join(str(p) for p in e.path) or "<root>"
            print(f"[SCHEMA] {loc}: {e.message}", file=sys.stderr)
        if errors:
            rc = 1
        else:
            print("[SCHEMA] OK")
    except ImportError:
        missing = [k for k in schema.get("required", []) if k not in data]
        if missing:
            print(f"[BASIC] нет обязательных полей: {missing}", file=sys.stderr)
            rc = 1
        else:
            print("[BASIC] jsonschema не установлен; проверены только обязательные поля верхнего уровня — OK")
    for e in check_refs(data):
        print(f"[REF] {e}", file=sys.stderr)
        rc = 1
    for w in check_sums(data):
        print(f"[SUM] {w}", file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
