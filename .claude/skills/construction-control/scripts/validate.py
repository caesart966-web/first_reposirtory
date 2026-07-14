#!/usr/bin/env python3
"""Валидация выходного JSON агентов по JSON Schema.

Каждый агент обязан вернуть JSON, проходящий валидацию по своей схеме из ../schemas.
Оркестратор вызывает это перед сохранением результата в БД.

Использование:
    python3 validate.py <schema_name> <data.json>
    echo '<json>' | python3 validate.py visual-progress.output -
Примеры schema_name: entities, issue, document-extraction.output,
    visual-progress.output, schedule-control.output, quality-control.output,
    weekly-report.output

Требуется пакет jsonschema (pip install jsonschema). Если он не установлен,
скрипт делает базовую структурную проверку и предупреждает.
"""
from __future__ import annotations

import json
import os
import sys

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "..", "schemas")


def load_json(path: str):
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_schema(name: str) -> str:
    if not name.endswith(".json"):
        name = name + ".schema.json"
    path = os.path.join(SCHEMA_DIR, name)
    if not os.path.exists(path):
        raise SystemExit(f"schema not found: {path}")
    return path


def validate(schema_name: str, data_path: str) -> int:
    schema_path = resolve_schema(schema_name)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    data = load_json(data_path)

    try:
        import jsonschema
        from jsonschema import Draft202012Validator
    except ImportError:
        # Мягкая деградация: без jsonschema делаем лишь проверку required верхнего уровня.
        required = schema.get("required", [])
        missing = [k for k in required if k not in (data or {})]
        if missing:
            print(f"[BASIC] missing required top-level fields: {missing}", file=sys.stderr)
            return 1
        print("[BASIC] jsonschema не установлен; проверены только required верхнего уровня — OK")
        return 0

    # Ссылки между схемами разрешаем через локальный registry по $id/имени файла.
    store = {}
    for fn in os.listdir(SCHEMA_DIR):
        if fn.endswith(".json"):
            with open(os.path.join(SCHEMA_DIR, fn), "r", encoding="utf-8") as f:
                s = json.load(f)
            if "$id" in s:
                store[s["$id"]] = s
            store[fn] = s  # по имени файла (относительные $ref вида entities.schema.json)

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        resolver = jsonschema.RefResolver(base_uri="", referrer=schema, store=store)
        validator = Draft202012Validator(schema, resolver=resolver)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        for e in errors:
            loc = "/".join(str(p) for p in e.path) or "<root>"
            print(f"[INVALID] {loc}: {e.message}", file=sys.stderr)
        return 1
    print("[VALID] OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(validate(sys.argv[1], sys.argv[2]))
