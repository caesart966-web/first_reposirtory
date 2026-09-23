"""Обёртка над скриптами скилла sro-odo: они и есть движок, здесь только вызовы."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .config import ENGINE_DIR, SCRIPTS_DIR

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import assess as _assess          # noqa: E402
import cases as _cases            # noqa: E402
import objection as _objection    # noqa: E402

DATA = SCRIPTS_DIR / "data"
SCHEMAS = ENGINE_DIR / "schemas"

# База прецедентов по умолчанию — в скилле (общая с Claude Code). ODO_CASES_DIR переносит её
# в другое место: так тесты и демо не пишут в настоящую базу.
_cases_dir = os.environ.get("ODO_CASES_DIR")
if _cases_dir:
    _cases.CASES_DIR = os.path.abspath(_cases_dir)
    _cases.INDEX = os.path.join(_cases.CASES_DIR, "index.jsonl")
    os.makedirs(_cases.CASES_DIR, exist_ok=True)


def load_json(p: Path):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def law() -> dict:
    return load_json(DATA / "law.json")["norms"]


def policy() -> dict:
    return load_json(DATA / "policy.json")


def levels() -> dict:
    return load_json(DATA / "levels.json")


def objection_catalogue() -> dict:
    return load_json(DATA / "objections.json")["claims"]


def card_schema() -> dict:
    return load_json(SCHEMAS / "contract-card.schema.json")


def validate_card(card: dict) -> list[str]:
    import jsonschema
    v = jsonschema.Draft202012Validator(card_schema())
    return [f"{'/'.join(str(x) for x in e.path) or '·'}: {e.message}" for e in v.iter_errors(card)]


def assess_card(card: dict, find_cases: bool = True) -> tuple[dict, str]:
    a = _assess.Assessor().assess(card, find_cases=find_cases)
    return a, _assess.markdown(a)


def analyze_letter(obj: dict, card: dict | None, assessment: dict | None) -> tuple[dict, str]:
    an = _objection.analyze(obj, card, assessment)
    return an, _objection.markdown(an)


def add_precedent_from_assessment(a: dict, decision: str, note: str | None, by: str | None) -> str:
    case = _cases.case_from_assessment(a, decision, note, by)
    return _cases.add_case(case)


def add_precedent_from_objection(o: dict, decision: str, note: str | None, by: str | None) -> str:
    case = _cases.case_from_objection(o, decision, note, by)
    return _cases.add_case(case)


def precedents() -> list[dict]:
    return _cases.load_index()


def rule_suggestions() -> list:
    return _cases.suggest(_cases.load_index())


def money(x) -> str:
    return _assess.money(x)


def engine_tests() -> dict:
    """Быстрый самоконтроль движка: прогон тестов скилла (для страницы настроек)."""
    import subprocess
    if getattr(sys, "frozen", False):
        return {"тесты": "в собранном приложении не запускаются; движок проверен при сборке"}
    out = {}
    for t in ("test_assess.py", "test_rules.py"):
        r = subprocess.run([sys.executable, str(SCRIPTS_DIR / t)], capture_output=True, text=True, cwd=str(SCRIPTS_DIR), timeout=120)
        out[t] = (r.stdout.strip().splitlines() or [""])[-1] + (("\n" + r.stderr.strip()) if r.returncode else "")
    return out
