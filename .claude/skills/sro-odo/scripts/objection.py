#!/usr/bin/env python3
"""Разбор письма компании, оспаривающей учёт договора в совокупном размере
обязательств: каждый довод проверяется юридическим тестом из каталога
data/objections.json и получает статус — обоснован / частично / не обоснован /
нужны факты — с нормами закона. На выходе анализ и проект ответа.

    python3 objection.py objection.json [--card card.json] [--assessment a.json] -o analysis.json --md reply.md

Claude заполняет objection.json: извлекает из письма утверждения (quote),
подбирает им type из каталога и записывает факты, подтверждённые документами.
Факты из карточки договора подставляются автоматически, факты претензии
имеют приоритет.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)

STATUS_RU = {"founded": "обоснован", "partially": "частично обоснован", "unfounded": "не обоснован", "needs_facts": "нужны факты", "needs_human": "решает человек"}
OVERALL_RU = {"founded": "обоснованы", "partially": "частично обоснованы", "unfounded": "не обоснованы", "needs_facts": "требуют документов или решения человека"}
HOUSING_EXCLUDED = {"izhs", "blocked", "mkd_low", "garden", "auxiliary"}
QUALIFYING = {"developer", "technical_customer", "operator", "regional_operator"}
SUBCONTRACT = {"general_contractor", "contractor", "other"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def facts_from_card(card: dict | None, assessment: dict | None) -> dict:
    f = {}
    if card:
        c, cu, ob = card["contract"], card["customer"], card["object"]
        price = c.get("price_rub")
        for a in c.get("addenda") or []:
            if a.get("price_rub") is not None:
                price = a["price_rub"]
        f.update({"contract_kind": c.get("kind"), "mixed_parts": c.get("mixed_parts") or [], "price_rub": price, "procurement": c.get("procurement"),
                  "status": c.get("status"), "executed_rub": c.get("executed_rub"), "has_final_act": c.get("has_final_act"),
                  "termination_document": c.get("termination_document"), "contract_date": c.get("date"), "customer_kind": cu.get("kind"),
                  "customer_kind_basis": cu.get("kind_basis"), "object_is_capital": ob.get("is_capital"), "permit_required": ob.get("permit_required"),
                  "housing_type": ob.get("housing_type", "unknown"), "object_category": ob.get("category"), "work_type": card.get("work_type"),
                  "contractor_is_state_entity": card["member"].get("is_state_entity"), "membership_date": card["member"].get("membership_date"),
                  "works": card.get("works", [])})
        sup = [p for p in (c.get("mixed_parts") or []) if p["kind"] == "supply"]
        if sup:
            f["supply_separately_priced"] = all(p.get("amount_rub") is not None for p in sup)
            f["supply_amount_rub"] = sum(p.get("amount_rub") or 0 for p in sup)
    if assessment:
        v = assessment["verdict"]
        f["share_sro"] = v.get("share_sro")
        f["auto_membership"] = v.get("membership_required")
        f["auto_counts"] = v.get("counts_for_odo")
    return f


def fmt(x):
    return "—" if x is None else f"{x:,.2f}".replace(",", "\u00a0").replace(".", ",")


# ---- тесты по типам доводов ------------------------------------------
def t_not_podryad(f):
    k = f.get("contract_kind")
    if k in ("supply", "services", "rent"):
        return "founded", f"По содержанию обязательств договор — {({'supply': 'поставка', 'services': 'услуги', 'rent': 'аренда'})[k]}, а не подряд: результата работ на объекте нет. Членство не требуется, в совокупный размер не входит.", ["gk-506" if k == "supply" else "gk-779" if k == "services" else "gk-606", "gk-702", "grk-52-2.1"]
    if k in ("construction", "demolition", "design", "survey"):
        return "unfounded", "Предмет договора — результат работ, который подрядчик сдаёт, а заказчик принимает по акту: это подряд независимо от названия договора. Монтажные, пусконаладочные и связанные работы охватываются строительным подрядом.", ["gk-702", "gk-740", "gk-431", "gk-753"]
    if k == "mixed":
        parts = f.get("mixed_parts") or []
        pod = [p for p in parts if p["kind"] in ("construction", "demolition", "design", "survey")]
        if pod:
            return "partially", "Договор смешанный: части поставки и услуг из расчёта исключаются, части-подряды учитываются. К каждой части применяются правила о соответствующем договоре.", ["gk-421-3", "gk-431", "grk-52-2.1"]
        return "needs_facts", "Заявлен смешанный договор, но состав частей не установлен.", ["gk-421-3", "gk-431"]
    return "needs_facts", "Вид договора не установлен: нужно проверить, есть ли овеществлённый результат работ и порядок его сдачи-приёмки.", ["gk-431", "gk-702", "gk-753"]


def t_not_capital(f):
    if f.get("object_is_capital") is False:
        return "founded", "Объект не является объектом капитального строительства: работы на нём — не строительство, реконструкция или капитальный ремонт ОКС.", ["grk-1-10", "grk-1-10.2", "grk-52-2.1"]
    if f.get("housing_type") in HOUSING_EXCLUDED:
        return "founded", "Объект выведен из-под Перечня и обязательного членства (ИЖС, садовый дом, вспомогательная постройка, блокированный или малоэтажный дом).", ["grk-51-17", "order-624-p2"]
    if f.get("work_type") in ("current_repair", "improvement"):
        return "founded", "Характер работ — текущий ремонт или благоустройство: это не капитальный ремонт по п. 14.2 ст. 1 ГрК РФ и не строительный подряд на ОКС для целей членства.", ["grk-1-14.2", "grk-52-2.1"]
    if f.get("work_type") == "capital_repair":
        return "unfounded", "Разрешение на строительство для капитального ремонта действительно не требуется, но капитальный ремонт объекта капитального строительства — работы, на которые распространяется обязательное членство (ч. 2.1 ст. 52 ГрК РФ говорит о договоре строительного подряда; ст. 740 ГК РФ охватывает капремонт).", ["grk-51-17", "grk-1-14.2", "gk-740", "grk-52-2.1"]
    if f.get("object_is_capital") is True:
        return "unfounded", "Объект — здание, строение или сооружение, то есть объект капитального строительства; довод о некапитальном характере не подтверждается.", ["grk-1-10", "grk-52-2.1"]
    return "needs_facts", "Характер объекта не установлен: нужны выписка ЕГРН, разрешение на строительство или проектная документация.", ["grk-1-10", "grk-51-17"]


def t_customer(f):
    ck = f.get("customer_kind")
    b = f" Подтверждение: {f['customer_kind_basis']}." if f.get("customer_kind_basis") else ""
    if ck in SUBCONTRACT:
        return "founded", "Заказчик по договору — не застройщик, не технический заказчик, не эксплуатант и не региональный оператор: это субподряд, членства не требует и в совокупный размер не входит." + b, ["grk-52-2.1", "grk-48-4.1", "grk-47-2.1", "grk-55.13-n"]
    if ck == "developer":
        return "unfounded", "Заказчик — застройщик: лицо, обеспечивающее строительство на принадлежащем ему участке. Договор с ним требует членства и входит в совокупный размер." + b, ["grk-1-16", "grk-52-2.1"]
    if ck == "technical_customer":
        return "unfounded", "Заказчик — технический заказчик, прямо названный в ч. 2.1 ст. 52 наравне с застройщиком. Договор с ним — не субподряд." + b, ["grk-1-22", "grk-52-4", "grk-52-2.1"]
    if ck in ("operator", "regional_operator"):
        return "unfounded", "Лицо, ответственное за эксплуатацию здания (собственник, УК, ТСЖ), и региональный оператор приравнены законом к застройщику для целей членства." + b, ["grk-52-2.1"]
    if ck == "individual":
        return "needs_facts", "Заказчик — физическое лицо. Если объект — ИЖС, садовый дом или вспомогательная постройка, довод обоснован; если физлицо обеспечивает строительство иного ОКС на своём участке — оно застройщик.", ["grk-1-16", "grk-51-17", "order-624-p2"]
    if ck == "state_entity":
        return "needs_facts", "Заказчик — учреждение или предприятие. Обычно оно застройщик либо технический заказчик — тогда довод не работает. Нужно подтверждение статуса: разрешение на строительство, контракт, полномочия.", ["grk-1-16", "grk-1-22", "grk-52-2.2"]
    return "needs_facts", "Статус заказчика не установлен: нужны разрешение на строительство, проектная декларация или договор о передаче функций технического заказчика.", ["grk-1-16", "grk-1-22", "grk-52-2.1"]


def t_threshold(f):
    k, p = f.get("contract_kind"), f.get("price_rub")
    if k in ("design", "survey"):
        return "unfounded", "Для проектирования и изысканий суммового порога нет: договор с застройщиком или техзаказчиком требует членства при любой цене.", ["grk-48-4.1", "grk-47-2.1"]
    thr = 10_000_000 if k == "construction" else 1_000_000 if k == "demolition" else None
    if thr is None:
        if k == "mixed":
            return "needs_facts", "Для смешанного договора порог применяется к строительной части: нужны цены частей.", ["gk-421-3", "grk-52-2.1"]
        return "needs_facts", "Вид договора не установлен, порог зависит от вида.", ["grk-52-2.1", "grk-55.31-5"]
    if p is None:
        return "needs_facts", "Цена договора с учётом дополнительных соглашений не установлена.", ["grk-52-2.1"]
    if p <= thr:
        return "founded", f"Размер обязательств {fmt(p)} ₽ не превышает {fmt(thr)} ₽: обязательного членства по этому договору нет. Считать ли такой договор в совокупном размере члена СРО — по положению СРО. Если один объём работ разбит на несколько договоров ниже порога, СРО вправе оценить это как обход.", ["grk-52-2.1" if k == "construction" else "grk-55.31-5", "fz-124"]
    return "unfounded", f"Размер обязательств {fmt(p)} ₽ выше порога {fmt(thr)} ₽ (с учётом дополнительных соглашений).", ["grk-52-2.1" if k == "construction" else "grk-55.31-5", "fz-124"]


def t_competitive(f):
    pr = f.get("procurement")
    pos = f.get("sro_position_competitive_only")
    if pr == "competitive":
        return "unfounded", "Договор заключён конкурентным способом: входит в совокупный размер при любом прочтении ч. 3 ст. 55.8 ГрК РФ.", ["grk-55.8-3", "fz-44", "fz-223"]
    if pr == "direct":
        if pos is True:
            return "founded", "СРО считает совокупный размер только по договорам, заключённым конкурентным способом (буква ч. 3 ст. 55.8): прямой договор в него не входит, но уведомляется по 309-ФЗ.", ["grk-55.8-3", "grk-55.13-n"]
        if pos is False:
            return "unfounded", "СРО учитывает все договоры подряда с застройщиком и техзаказчиком (после 309-ФЗ из ч. 6 ст. 55.8 исключены слова о конкурентных способах): прямой договор входит.", ["grk-55.8-6", "fz-309", "grk-55.13-n"]
        return "partially", "По букве ч. 3 ст. 55.8 совокупный размер считается по конкурентным договорам, и прямой договор в него не входит. После 309-ФЗ (с 01.03.2026) уведомляются все договоры подряда, а из ч. 6 ст. 55.8 оговорка о конкурентных способах исключена. Итог зависит от положения о контроле СРО; довод нельзя ни принять, ни отклонить без него.", ["grk-55.8-3", "grk-55.8-6", "fz-309", "grk-55.13-n"]
    return "needs_facts", "Способ заключения договора не установлен.", ["grk-55.8-3"]


def t_executed(f):
    if f.get("has_final_act"):
        return "founded", "Результат принят по акту: обязательства, признанные исполненными, в фактический совокупный размер не включаются. Об исполнении подаётся уведомление в СРО.", ["grk-55.13-4", "gk-753", "grk-55.13-n"]
    ex, p = f.get("executed_rub"), f.get("price_rub")
    if ex is not None and p is not None and ex > 0:
        return "partially", f"Принято по актам {fmt(ex)} ₽ из {fmt(p)} ₽: исполненная часть из расчёта исключается, остаток {fmt(max(p - ex, 0))} ₽ учитывается. Договор не снимается с учёта до итогового акта.", ["grk-55.13-4", "gk-753"]
    return "needs_facts", "Актов приёмки (КС-2, КС-11, итоговый акт) не представлено: без них исполнение не подтверждено.", ["grk-55.13-4", "gk-753"]


def t_terminated(f):
    if f.get("termination_document"):
        return "founded", f"Расторжение подтверждено ({f['termination_document']}): с даты расторжения обязательств нет, принятые до этого работы — по актам. О расторжении уведомляется СРО.", ["grk-55.13-n", "grk-55.13-4"]
    return "needs_facts", "Документ о расторжении (соглашение, уведомление об одностороннем отказе с датой) не представлен.", ["grk-55.13-n"]


def t_works_not_in_list(f):
    if f.get("work_type") in ("current_repair", "improvement"):
        return "founded", "Весь предмет договора — работы вне строительства, реконструкции и капитального ремонта (текущий ремонт, благоустройство): это не строительный подряд на ОКС.", ["grk-1-14.2", "grk-52-2.1", "fz-372"]
    sh = f.get("share_sro")
    if sh is None:
        return "needs_facts", "Виды работ по договору не разобраны: нужна смета или перечень работ, чтобы разделить цену по Перечню 624.", ["order-624", "fz-372"]
    if sh == 0:
        return "founded", "Все виды работ по договору отсутствуют в Перечне 624 либо помечены «*» и выполняются на обычном объекте: к работам, влияющим на безопасность, они не относятся.", ["order-624", "order-624-note", "letter-33838", "fz-372"]
    if sh < 1:
        return "partially", f"С 01.07.2017 членство определяется договором, а не видом работ: договор строительного подряда с застройщиком выше порога требует членства целиком. Для разделения цены довод учтён: {(1 - sh) * 100:.0f} % цены — работы вне Перечня или со знаком «*» на обычном объекте — в «СРО» не идут, {sh * 100:.0f} % — идут.", ["fz-372", "grk-52-2.1", "order-624", "order-624-note", "letter-33838"]
    return "unfounded", "Все виды работ по договору входят в Перечень 624 без знака «*» либо на объекте ст. 48.1: это работы, влияющие на безопасность. Кроме того, с 01.07.2017 членство определяется договором, а не видом работ.", ["order-624", "fz-372", "grk-52-2.1"]


def t_state_exempt(f):
    if f.get("contractor_is_state_entity") is True:
        return "founded", "Подрядчик — ГУП, МУП, учреждение или организация с публичным участием более 50 %: обязательное членство на него не распространяется.", ["grk-52-2.2"]
    if f.get("contractor_is_state_entity") is False:
        return "unfounded", "Исключение ч. 2.2 ст. 52 ГрК РФ касается подрядчика, а не заказчика. То, что заказчик — учреждение, от членства подрядчика не освобождает; напротив, учреждение-заказчик обычно застройщик или технический заказчик.", ["grk-52-2.2", "grk-52-2.1", "grk-1-22"]
    return "needs_facts", "Не установлено, подпадает ли сам подрядчик под ч. 2.2 ст. 52 ГрК РФ (выписка ЕГРЮЛ, состав участников).", ["grk-52-2.2"]


def t_housing(f):
    ht = f.get("housing_type")
    if ht in HOUSING_EXCLUDED:
        return "founded", "Объект — ИЖС, садовый дом, вспомогательная постройка либо блокированный или малоэтажный дом: разрешение на строительство не требуется, Перечень не распространяется, обязательного членства нет.", ["grk-51-17", "order-624-p2"]
    if ht == "none":
        return "unfounded", "Объект не относится к ИЖС, садовым домам, вспомогательным постройкам и малоэтажным домам, выведенным из-под Перечня.", ["grk-51-17", "order-624-p2", "grk-52-2.1"]
    return "needs_facts", "Вид объекта не подтверждён: нужны уведомление о планируемом строительстве, выписка ЕГРН, проектная документация.", ["grk-51-17", "order-624-p2"]


def t_design_threshold(f):
    if f.get("contract_kind") in ("design", "survey"):
        return "unfounded", "Порог 10 млн ₽ установлен только для строительного подряда. Для подготовки проектной документации и инженерных изысканий суммового порога нет.", ["grk-48-4.1", "grk-47-2.1", "grk-52-2.1"]
    return "unfounded", "Довод о пороге для проектирования неприменим: договор не проектный.", ["grk-52-2.1"]


def t_tech_customer(f):
    if f.get("customer_kind") == "technical_customer":
        return "unfounded", "Технический заказчик прямо назван в ч. 2.1 ст. 52, ч. 4.1 ст. 48 и ч. 2.1 ст. 47 ГрК РФ рядом с застройщиком: договор с ним требует членства и входит в совокупный размер. Проверяется лишь наличие у контрагента функций техзаказчика (договор с застройщиком, п. 22 ст. 1).", ["grk-1-22", "grk-52-4", "grk-52-2.1"]
    return "needs_facts", "Статус контрагента как технического заказчика не подтверждён.", ["grk-1-22"]


def t_before_2026(f):
    if f.get("executed_before_2026_03_01") and f.get("has_final_act"):
        return "founded", "Договор полностью исполнен до 1 марта 2026 года: под уведомление по 309-ФЗ не попадает, обязательств по нему нет.", ["fz-309", "grk-55.13-4"]
    return "unfounded", "Дата заключения значения не имеет: под уведомление и учёт попадают все договоры, по которым на 1 марта 2026 года оставались неисполненные обязательства.", ["fz-309", "grk-55.13-n", "grk-55.13-4"]


def t_supply(f):
    if f.get("supply_separately_priced") and f.get("supply_amount_rub"):
        return "partially", f"Поставка выделена в предмете и цене как самостоятельное обязательство ({fmt(f['supply_amount_rub'])} ₽): эта часть смешанного договора из расчёта исключается. Материалы и оборудование, использованные подрядчиком при выполнении работ, из цены работ не вычитаются.", ["gk-421-3", "gk-704", "gk-745", "gk-506"]
    return "unfounded", "Материалы и оборудование, которыми подрядчик обеспечивает работы, — часть стоимости работ, а не отдельная поставка; вычесть их из цены договора нельзя. Исключается только выделенное в договоре самостоятельное обязательство поставки.", ["gk-704", "gk-745", "gk-421-3", "gk-740"]


def t_not_member(f):
    return "unfounded", "Совокупный размер обязательств считается по действующим договорам члена СРО на дату расчёта независимо от даты вступления. Выполнение работ без членства, когда оно требовалось, — отдельное нарушение, а не основание исключить договор.", ["grk-55.8-3", "grk-55.13-4", "grk-52-2.1"]


TESTS = {"not_podryad": t_not_podryad, "not_capital_object": t_not_capital, "customer_not_developer": t_customer, "below_threshold": t_threshold,
         "not_competitive": t_competitive, "executed": t_executed, "terminated": t_terminated, "works_not_in_list": t_works_not_in_list,
         "state_exempt": t_state_exempt, "individual_housing": t_housing, "design_threshold": t_design_threshold,
         "technical_customer_is_intermediary": t_tech_customer, "before_2026": t_before_2026, "price_includes_supply": t_supply,
         "not_member_at_signing": t_not_member}


def analyze(obj: dict, card: dict | None, assessment: dict | None) -> dict:
    catalogue = load_json(os.path.join(DATA, "objections.json"))["claims"]
    law = load_json(os.path.join(DATA, "law.json"))["norms"]
    base = facts_from_card(card, assessment)
    used, claims_out = set(), []
    for cl in obj["claims"]:
        f = dict(base)
        f.update(cl.get("facts") or {})
        t = cl["type"]
        if t in TESTS:
            status, expl, basis = TESTS[t](f)
            cat = catalogue.get(t, {})
            missing = [k for k in cat.get("facts", []) if f.get(k) is None] if status == "needs_facts" else []
        else:
            status, expl, basis, cat, missing = "needs_human", "Довод не относится к типовым: оценивает человек.", [], {}, []
        used.update(basis)
        claims_out.append({"type": t, "title": cat.get("title", "Иной довод"), "quote": cl["quote"], "status": status, "explanation": expl,
                           "basis": basis, "test": cat.get("test"), "missing": missing,
                           "facts_used": {k: f.get(k) for k in cat.get("facts", []) if k in f}})
    st = [c["status"] for c in claims_out]
    if "founded" in st and all(s in ("founded", "unfounded", "partially") for s in st):
        overall = "founded"
    elif "needs_facts" in st or "needs_human" in st:
        overall = "needs_facts"
    elif "partially" in st:
        overall = "partially"
    else:
        overall = "unfounded"
    effect = None
    if overall == "founded":
        effect = "Хотя бы один довод обоснован: договор из совокупного размера исключается (или уменьшается остаток) — см. доводы со статусом «обоснован»."
    elif overall == "partially":
        effect = "Доводы частично обоснованы: договор остаётся в учёте, меняется его состав или сумма — см. пояснения."
    elif overall == "unfounded":
        effect = "Ни один довод не обоснован: договор учитывается в совокупном размере в полном объёме остатка."
    else:
        effect = "Часть доводов требует документов или решения человека: до их получения позиция не окончательна."
    return {"letter": obj["letter"], "claims": claims_out, "overall": overall, "overall_ru": OVERALL_RU[overall], "effect": effect,
            "law_index": {i: law[i] for i in sorted(used) if i in law},
            "verification_note": "Нормы приведены по реестру law.json без сверки с официальным текстом; перед отправкой ответа сверить формулировки."}


def markdown(an: dict) -> str:
    law = an["law_index"]

    def cites(ids):
        return "; ".join(law[i]["cite"] for i in ids if i in law)

    L = an["letter"]
    out = [f"# Разбор письма {L['from']}" + (f" от {L['date']}" if L.get("date") else "") + (f" № {L['number']}" if L.get("number") else ""),
           f"Суть письма: {L['summary']}" + (f" Договор: {L['contract_number']}." if L.get("contract_number") else ""), "",
           f"**Итог: доводы {an['overall_ru']}.** {an['effect']}", "", "## Доводы и их оценка", ""]
    for i, c in enumerate(an["claims"], 1):
        out.append(f"### {i}. {c['title']} — {STATUS_RU[c['status']]}")
        out.append(f"> {c['quote']}")
        out.append("")
        out.append(c["explanation"])
        if c["basis"]:
            out.append(f"*Основание:* {cites(c['basis'])}.")
        if c["missing"]:
            out.append("*Нужно представить:* " + "; ".join(c["missing"]) + ".")
        out.append("")
    out += ["## Проект ответа", "", f"Уважаемые коллеги! Рассмотрев ваше письмо" + (f" от {L['date']}" if L.get("date") else "") + ", сообщаем следующее.", ""]
    for i, c in enumerate(an["claims"], 1):
        verdict = {"founded": "Довод принимается.", "partially": "Довод принимается частично.", "unfounded": "Довод не может быть принят.",
                   "needs_facts": "Для оценки довода необходимы документы.", "needs_human": "Довод будет рассмотрен дополнительно."}[c["status"]]
        out.append(f"{i}. По доводу о том, что {c['quote'].rstrip('.').lower()}. {verdict} {c['explanation']}" + (f" Основание: {cites(c['basis'])}." if c["basis"] else "")
                   + (f" Просим представить: {'; '.join(c['missing'])}." if c["missing"] else ""))
        out.append("")
    out += [an["effect"], "", "## Нормы", ""] + [f"- **{n['cite']}** — {n['gist']}" for n in law.values()] + ["", f"> {an['verification_note']}"]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("objection")
    ap.add_argument("--card")
    ap.add_argument("--assessment")
    ap.add_argument("-o", "--out")
    ap.add_argument("--md")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    obj = load_json(args.objection)
    card = load_json(args.card) if args.card else None
    assessment = load_json(args.assessment) if args.assessment else None
    an = analyze(obj, card, assessment)
    obj["analysis"] = an
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
    md = markdown(an)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(md)
    if not args.quiet:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
