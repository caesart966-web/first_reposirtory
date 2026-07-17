"""Валидация выходных данных по JSON Schema скилла (единый источник истины).

Схемы берутся из .claude/skills/construction-control/schemas. Кросс-ссылки между
схемами (issue -> entities) резолвятся локальным registry по $id и имени файла.
Если каталог схем не найден (backend упакован отдельно) — валидация мягко
отключается с предупреждением.
"""
from __future__ import annotations

import json
import warnings
from functools import lru_cache
from typing import Any

from . import config


class ValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


@lru_cache(maxsize=1)
def _load_store() -> dict[str, Any]:
    store: dict[str, Any] = {}
    if not config.SCHEMAS_DIR or not config.SCHEMAS_DIR.is_dir():
        return store
    for path in config.SCHEMAS_DIR.glob("*.json"):
        with open(path, "r", encoding="utf-8") as fh:
            schema = json.load(fh)
        if "$id" in schema:
            store[schema["$id"]] = schema
        store[path.name] = schema
    return store


def _resolve_name(name: str) -> str:
    return name if name.endswith(".json") else f"{name}.schema.json"


def validate(schema_name: str, data: Any) -> None:
    """Бросает ValidationError, если data не соответствует схеме schema_name.

    schema_name без расширения, напр. "issue", "visual-progress.output".
    """
    store = _load_store()
    key = _resolve_name(schema_name)
    schema = store.get(key)
    if schema is None:
        warnings.warn(f"schema '{key}' не найдена — валидация пропущена")
        return
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
    except ImportError:  # pragma: no cover
        required = schema.get("required", [])
        missing = [k for k in required if isinstance(data, dict) and k not in data]
        if missing:
            raise ValidationError([f"missing required: {missing}"])
        return

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        resolver = jsonschema.RefResolver(base_uri="", referrer=schema, store=store)
        validator = Draft202012Validator(schema, resolver=resolver)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        raise ValidationError([
            f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        ])


def is_valid(schema_name: str, data: Any) -> bool:
    try:
        validate(schema_name, data)
        return True
    except ValidationError:
        return False


def validate_entity(entity_type: str, data: Any) -> None:
    """Валидация одной сущности против entities.schema.json#/$defs/<entity_type>."""
    store = _load_store()
    if "entities.schema.json" not in store:
        warnings.warn("entities.schema.json не найдена — валидация сущности пропущена")
        return
    ref_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": f"entities.schema.json#/$defs/{entity_type}",
    }
    try:
        import jsonschema
        from jsonschema import Draft202012Validator
    except ImportError:  # pragma: no cover
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        resolver = jsonschema.RefResolver(base_uri="", referrer=ref_schema, store=store)
        validator = Draft202012Validator(ref_schema, resolver=resolver)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        raise ValidationError([
            f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        ])


def is_valid_entity(entity_type: str, data: Any) -> bool:
    try:
        validate_entity(entity_type, data)
        return True
    except ValidationError:
        return False
