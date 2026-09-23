"""Необязательное ИИ-извлечение карточки из текста: включается ключом ANTHROPIC_API_KEY.

Правила (parse_contract.py) хорошо читают контракты по 44-ФЗ. Для договоров
произвольной формы модель заполняет карточку по схеме, а человек проверяет её
в форме — как и черновик от правил. Числа, найденные правилами (цена, ИКЗ,
сроки), имеют приоритет: они детерминированы.
"""
from __future__ import annotations

import json

from .config import ANTHROPIC_API_KEY, LLM_MODEL

SYSTEM = (
    "Ты помощник проверяющего СРО. По тексту договора подряда и приложений заполни карточку договора строго по схеме. "
    "Ничего не выдумывай: чего нет в тексте — null или unknown. Поля *_basis — цитата или пункт документа, откуда взят факт. "
    "customer.kind: developer — застройщик (есть разрешение на строительство); technical_customer; operator — лицо, ответственное "
    "за эксплуатацию (учреждение, владеющее зданием); regional_operator — фонд капремонта; general_contractor — генподрядчик "
    "(тогда это субподряд); state_entity — орган власти; unknown — не ясно. procurement: competitive только для 44-ФЗ, 223-ФЗ или "
    "обязательных по закону торгов; добровольный тендер — competitive + procurement_law=voluntary_tender. "
    "work_type: capital_repair, если сметы по Методике 421/пр или в тексте «капитальный ремонт». works — строки смет с суммами без НДС."
)


def available() -> bool:
    return bool(ANTHROPIC_API_KEY)


def extract_card(docs: list[dict], schema: dict, member: dict) -> dict | None:
    """docs: [{filename, kind, text}] → карточка по схеме или None (ключа нет / ошибка)."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    parts = []
    for d in docs:
        if d.get("text"):
            parts.append(f"### Файл: {d['filename']} (тип: {d['kind']})\n{d['text'][:60000]}")
    if not parts:
        return None
    tool_schema = json.loads(json.dumps(schema))
    tool_schema.pop("$schema", None)
    tool_schema.pop("$id", None)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        msg = client.messages.create(
            model=LLM_MODEL, max_tokens=8000, system=SYSTEM,
            tools=[{"name": "fill_card", "description": "Заполнить карточку договора по схеме", "input_schema": tool_schema}],
            tool_choice={"type": "tool", "name": "fill_card"},
            messages=[{"role": "user", "content": f"Член СРО (подрядчик): {member.get('name')} ИНН {member.get('inn') or '—'}.\n\n" + "\n\n".join(parts)}],
        )
    except Exception:
        return None
    for block in msg.content:
        if getattr(block, "type", "") == "tool_use" and block.name == "fill_card":
            return block.input
    return None


def merge(rule_card: dict, llm_card: dict | None, meta: dict) -> tuple[dict, dict]:
    """Карточка модели как основа, детерминированные поля правил — сверху."""
    if not llm_card:
        return rule_card, meta
    card = json.loads(json.dumps(llm_card))
    rc = rule_card["contract"]
    for k in ("number", "price_rub", "price_includes_vat", "period_from", "period_to", "nmck_rub", "procurement_basis", "addenda", "executed_rub"):
        if rc.get(k) not in (None, "", []):
            card["contract"][k] = rc[k]
    if rule_card["customer"].get("inn"):
        card["customer"]["inn"] = rule_card["customer"]["inn"]
    if rule_card["works"] and not card.get("works"):
        card["works"] = rule_card["works"]
    card["member"] = rule_card["member"]
    card["sources"] = rule_card["sources"]
    card.setdefault("schema_version", "1")
    meta = dict(meta)
    meta["source"] = "rules+llm"
    meta["needs_review"] = [k for k in meta.get("needs_review", []) if k not in ("customer_kind", "work_type", "customer_name")]
    return card, meta
