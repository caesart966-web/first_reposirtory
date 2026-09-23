#!/usr/bin/env python3
"""Тесты режимов «оценка договора» и «разбор возражений» на вымышленных карточках.

    python3 test_assess.py
"""
from __future__ import annotations

import copy
import sys

from assess import Assessor
from objection import analyze


def card(**over):
    base = {
        "schema_version": "1",
        "member": {"name": "Подрядчик", "inn": None, "role": "contractor", "is_state_entity": False, "sro_kinds": ["build"], "membership_date": None},
        "contract": {"number": "1", "date": "2026-05-01", "subject_text": "Строительство здания", "kind": "construction", "kind_basis": None, "mixed_parts": [],
                     "price_rub": 50_000_000.0, "price_basis": None, "price_includes_vat": True, "addenda": [], "status": "active", "status_basis": None,
                     "period_from": None, "period_to": None, "procurement": "competitive", "procurement_basis": None, "executed_rub": None,
                     "executed_basis": None, "has_final_act": None, "termination_document": None},
        "customer": {"name": "Застройщик", "inn": None, "kind": "developer", "kind_basis": "разрешение на строительство"},
        "object": {"name": "Здание", "address": None, "cadastral": None, "is_capital": True, "permit_required": True, "housing_type": "none", "category": "ordinary", "basis": None},
        "work_type": "construction", "works": [], "sources": [], "as_of": "2026-09-01", "notes": None,
    }
    c = copy.deepcopy(base)
    for k, v in over.items():
        path = k.split("__")
        d = c
        for pp in path[:-1]:
            d = d[pp]
        d[path[-1]] = v
    return c


CASES = [
    ("генподряд с застройщиком, торги, 50 млн", card(), "yes", "yes", "build"),
    ("прямой договор с застройщиком", card(contract__procurement="direct"), "yes", "no", "build"),
    ("субподряд у генподрядчика", card(customer__kind="general_contractor"), "no", "no", "build"),
    ("поставка", card(contract__kind="supply"), "no", "no", None),
    ("услуги охраны", card(contract__kind="services"), "no", "no", None),
    ("капремонт 8 млн, торги", card(contract__price_rub=8_000_000.0, work_type="capital_repair"), "no", "no", "build"),
    ("капремонт 8 млн, прямой", card(contract__price_rub=8_000_000.0, work_type="capital_repair", contract__procurement="direct"), "no", "no", "build"),
    ("капремонт 8 млн + ДС до 12 млн", card(contract__price_rub=8_000_000.0, contract__addenda=[{"number": "1", "price_rub": 12_000_000.0}], work_type="capital_repair"), "yes", "yes", "build"),
    ("проектирование 3 млн для техзаказчика", card(contract__kind="design", contract__price_rub=3_000_000.0, customer__kind="technical_customer", work_type="design"), "yes", "yes", "design"),
    ("изыскания 1 млн для застройщика", card(contract__kind="survey", contract__price_rub=1_000_000.0, work_type="survey"), "yes", "yes", "survey"),
    ("снос 900 тыс., торги", card(contract__kind="demolition", contract__price_rub=900_000.0, work_type="demolition"), "no", "no", "build"),
    ("снос 2 млн", card(contract__kind="demolition", contract__price_rub=2_000_000.0, work_type="demolition"), "yes", "yes", "build"),
    ("ИЖС для физлица", card(customer__kind="individual", object__housing_type="izhs", object__permit_required=False), "no", "no", "build"),
    ("косметический ремонт офиса для УК", card(customer__kind="operator", work_type="current_repair"), "no", "no", "build"),
    ("благоустройство для застройщика", card(work_type="improvement"), "no", "no", "build"),
    ("некапитальный объект", card(object__is_capital=False), "no", "no", "build"),
    ("член СРО — заказчик", card(member__role="customer"), "no", "no", "build"),
    ("подрядчик — МУП", card(member__is_state_entity=True), "no", "no", "build"),
    ("договор исполнен по акту", card(contract__status="completed", contract__has_final_act=True), "no", "no", "build"),
    ("расторгнут с документом", card(contract__status="terminated", contract__termination_document="соглашение от 01.08.2026"), "no", "no", "build"),
    ("расторжение без документа", card(contract__status="terminated"), "yes", "needs_facts", "build"),
    ("заказчик неизвестен", card(customer__kind="unknown"), "needs_facts", "needs_facts", "build"),
    ("заказчик — учреждение", card(customer__kind="state_entity"), "conditional", "conditional", "build"),
    ("вид договора неизвестен", card(contract__kind="unknown"), "needs_facts", "needs_facts", None),
    ("способ заключения неизвестен", card(contract__procurement="unknown"), "yes", "needs_facts", "build"),
    ("цена неизвестна", card(contract__price_rub=None), "needs_facts", "needs_facts", "build"),
    ("смешанный: проект + стройка 30 млн", card(contract__kind="mixed", contract__mixed_parts=[{"kind": "design", "amount_rub": 5_000_000.0}, {"kind": "construction", "amount_rub": 30_000_000.0}], work_type="mixed"), "yes", "yes", "mixed"),
    ("смешанный без цен частей", card(contract__kind="mixed", contract__mixed_parts=[{"kind": "supply"}, {"kind": "construction"}], work_type="mixed"), "conditional", "conditional", "build"),
    ("субподряд с торгов генподрядчика", card(customer__kind="general_contractor", contract__procurement="competitive"), "no", "no", "build"),
    ("эксплуатант, капремонт 15 млн", card(customer__kind="operator", contract__price_rub=15_000_000.0, work_type="capital_repair"), "yes", "yes", "build"),
    ("региональный оператор", card(customer__kind="regional_operator", work_type="capital_repair"), "yes", "yes", "build"),
]

WORK_CASES = [
    ("монолит на обычном объекте", "Устройство монолитных железобетонных конструкций", "ordinary", True),
    ("кладка на обычном объекте", "Кладка стен из кирпича", "ordinary", False),
    ("кладка на объекте 48.1", "Кладка стен из кирпича", "hazardous_48_1", True),
    ("отделка", "Штукатурка и окраска стен", "ordinary", False),
    ("поставка", "Поставка лифтового оборудования", "ordinary", False),
    ("монтаж лифтов", "Монтаж лифтов", "ordinary", True),
    ("звёздочка, категория неизвестна", "Устройство кровли из рулонных материалов", "unknown", None),
]

OBJECTION_CASES = [
    ("субподряд — обоснован", card(customer__kind="general_contractor"), "customer_not_developer", {}, "founded"),
    ("застройщик — не обоснован", card(), "customer_not_developer", {}, "unfounded"),
    ("техзаказчик как посредник", card(customer__kind="technical_customer"), "technical_customer_is_intermediary", {}, "unfounded"),
    ("порог 8 млн — обоснован", card(contract__price_rub=8_000_000.0), "below_threshold", {}, "founded"),
    ("порог 50 млн — нет", card(), "below_threshold", {}, "unfounded"),
    ("порог для проектирования", card(contract__kind="design", contract__price_rub=2_000_000.0), "design_threshold", {}, "unfounded"),
    ("прямой договор, практика проверяющего — только торги", card(contract__procurement="direct"), "not_competitive", {}, "founded"),
    ("прямой договор, СРО считает все", card(contract__procurement="direct"), "not_competitive", {"sro_position_competitive_only": False}, "unfounded"),
    ("прямой договор, СРО считает только торги", card(contract__procurement="direct"), "not_competitive", {"sro_position_competitive_only": True}, "founded"),
    ("торги", card(), "not_competitive", {}, "unfounded"),
    ("исполнен с актом", card(contract__has_final_act=True), "executed", {}, "founded"),
    ("исполнен частично", card(contract__executed_rub=20_000_000.0), "executed", {}, "partially"),
    ("исполнен без актов", card(), "executed", {}, "needs_facts"),
    ("заказчик-учреждение освобождает", card(customer__kind="state_entity"), "state_exempt", {"contractor_is_state_entity": False}, "unfounded"),
    ("подрядчик — ГУП", card(member__is_state_entity=True), "state_exempt", {}, "founded"),
    ("ИЖС", card(object__housing_type="izhs"), "individual_housing", {}, "founded"),
    ("не ИЖС", card(), "individual_housing", {}, "unfounded"),
    ("капремонт без разрешения", card(work_type="capital_repair"), "not_capital_object", {}, "unfounded"),
    ("некапитальный объект", card(object__is_capital=False), "not_capital_object", {}, "founded"),
    ("текущий ремонт", card(work_type="current_repair"), "works_not_in_list", {}, "founded"),
    ("поставка с монтажом — смешанный", card(contract__kind="mixed", contract__mixed_parts=[{"kind": "supply", "amount_rub": 10e6}, {"kind": "construction", "amount_rub": 30e6}]), "not_podryad", {}, "partially"),
    ("это услуги", card(contract__kind="services"), "not_podryad", {}, "founded"),
    ("материалы подрядчика", card(), "price_includes_supply", {}, "unfounded"),
    ("выделенная поставка", card(contract__kind="mixed", contract__mixed_parts=[{"kind": "supply", "amount_rub": 10e6}, {"kind": "construction", "amount_rub": 30e6}]), "price_includes_supply", {}, "partially"),
    ("договор 2024 года, действует", card(contract__date="2024-03-01"), "before_2026", {}, "unfounded"),
    ("договор 2024 года, исполнен до марта 2026", card(contract__date="2024-03-01", contract__has_final_act=True), "before_2026", {"executed_before_2026_03_01": True}, "founded"),
    ("не были членом при подписании", card(), "not_member_at_signing", {}, "unfounded"),
    ("нетиповой довод", card(), "other", {}, "needs_human"),
]


def main():
    A = Assessor()
    fails = []
    for name, c, m, o, k in CASES:
        a = A.assess(c, find_cases=False)
        v = a["verdict"]
        if (v["membership_required"], v["counts_for_odo"], v["sro_kind"]) != (m, o, k):
            fails.append(f"договор «{name}»: ожидалось {m}/{o}/{k}, получено {v['membership_required']}/{v['counts_for_odo']}/{v['sro_kind']}")
        for f in a["findings"]:
            if not f["basis"]:
                fails.append(f"договор «{name}»: шаг «{f['title']}» без основания")
    for name, text, cat, exp in WORK_CASES:
        c = card(object__category=cat, works=[{"name": text, "amount_rub": 1.0, "source": None}])
        w = A.assess(c, find_cases=False)["works"][0]
        if w["sro"] != exp or not w["basis"]:
            fails.append(f"работа «{name}»: ожидалось {exp}, получено {w['sro']} (основание: {w['basis']})")
    for name, c, t, facts, exp in OBJECTION_CASES:
        obj = {"schema_version": "1", "letter": {"from": "X", "date": None, "summary": ""}, "claims": [{"type": t, "quote": name, "facts": facts}]}
        an = analyze(obj, c, A.assess(c, find_cases=False))
        got = an["claims"][0]["status"]
        if got != exp:
            fails.append(f"довод «{name}»: ожидалось {exp}, получено {got}")
        if t != "other" and not an["claims"][0]["basis"]:
            fails.append(f"довод «{name}»: без основания")
    total = len(CASES) + len(WORK_CASES) + len(OBJECTION_CASES)
    print(f"случаев: {total}, расхождений: {len(fails)}")
    for f in fails:
        print("  ✗", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
