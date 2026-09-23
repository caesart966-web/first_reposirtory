#!/usr/bin/env python3
"""Заключение по одному договору: требуется ли членство в СРО и входит ли
договор в совокупный размер обязательств (КФ ОДО), с нормой закона под каждым
выводом и под каждым видом работ.

Вход — карточка договора (schemas/contract-card.schema.json), которую Claude
заполняет из текста договора и приложений. Выход — assessment.json
(schemas/assessment.schema.json) и заключение в Markdown.

    python3 assess.py card.json -o assessment.json --md zakl.md
    python3 assess.py card.json --no-cases      # без поиска прецедентов

Скрипт не решает за человека: статус заказчика, категорию объекта и вид
договора он берёт из карточки; где факта нет — пишет «нужно установить».
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
from classify import Classifier, norm  # noqa: E402

QUALIFYING = {"developer", "technical_customer", "operator", "regional_operator"}
SUBCONTRACT = {"general_contractor", "contractor", "other"}
PODRYAD = {"construction", "demolition", "design", "survey", "mixed"}
NON_PODRYAD = {"supply", "services", "rent", "other"}
KIND_SRO = {"construction": "build", "demolition": "build", "design": "design", "survey": "survey"}
KIND_RU = {"construction": "строительный подряд", "demolition": "подряд на снос", "design": "подряд на подготовку проектной документации",
           "survey": "подряд на инженерные изыскания", "mixed": "смешанный договор", "supply": "поставка", "services": "возмездное оказание услуг",
           "rent": "аренда", "other": "иной договор", "unknown": "вид не установлен"}
KIND_BASIS = {"construction": ["gk-740", "gk-702"], "demolition": ["gk-740", "grk-1-14.4"], "design": ["gk-758"], "survey": ["gk-758"],
              "mixed": ["gk-421-3", "gk-431"], "supply": ["gk-506"], "services": ["gk-779"], "rent": ["gk-606"], "other": ["gk-431"], "unknown": ["gk-431"]}
CUSTOMER_RU = {"developer": "застройщик", "technical_customer": "технический заказчик", "operator": "лицо, ответственное за эксплуатацию здания",
               "regional_operator": "региональный оператор", "general_contractor": "генеральный подрядчик", "contractor": "подрядчик",
               "individual": "физическое лицо", "state_entity": "государственное или муниципальное учреждение/предприятие", "other": "иное лицо", "unknown": "статус не установлен"}
CUSTOMER_BASIS = {"developer": ["grk-1-16"], "technical_customer": ["grk-1-22", "grk-52-4"], "operator": ["grk-55.25-1"], "regional_operator": ["grk-52-2.1"]}
HOUSING_EXCLUDED = {"izhs", "blocked", "mkd_low", "garden", "auxiliary"}
HOUSING_RU = {"izhs": "объект индивидуального жилищного строительства", "blocked": "жилой дом блокированной застройки до трёх этажей",
              "mkd_low": "многоквартирный дом до трёх этажей", "garden": "садовый дом", "auxiliary": "строение вспомогательного использования"}
WORK_TYPE_RU = {"construction": "строительство", "reconstruction": "реконструкция", "capital_repair": "капитальный ремонт", "demolition": "снос",
                "current_repair": "текущий (косметический) ремонт", "improvement": "благоустройство", "design": "проектирование", "survey": "изыскания",
                "mixed": "несколько видов", "unknown": "не установлено"}
WORK_TYPE_BASIS = {"construction": ["grk-1-13"], "reconstruction": ["grk-1-14"], "capital_repair": ["grk-1-14.2"], "demolition": ["grk-1-14.4"]}
SRO_RU = {"build": "строителей", "design": "проектировщиков", "survey": "изыскателей", "mixed": "нескольких видов"}
PRICE_BANDS = [(10e6, "до 10 млн ₽"), (90e6, "10–90 млн ₽"), (500e6, "90–500 млн ₽"), (3e9, "500 млн – 3 млрд ₽"), (10e9, "3–10 млрд ₽"), (None, "10 млрд ₽ и более")]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def r2(x):
    return None if x is None else round(float(x), 2)


def money(x) -> str:
    """148 000 000,00 — пробелы между разрядами, запятая в дробной части."""
    return "—" if x is None else f"{x:,.2f}".replace(",", "\u00a0").replace(".", ",")


def price_band(p):
    if p is None:
        return "не установлена"
    for lim, name in PRICE_BANDS:
        if lim is None or p < lim:
            return name
    return PRICE_BANDS[-1][1]


def effective_price(contract):
    price = contract.get("price_rub")
    for a in contract.get("addenda") or []:
        if a.get("price_rub") is not None:
            price = a["price_rub"]
    return price


class Assessor:
    def __init__(self):
        self.law = load_json(os.path.join(DATA, "law.json"))["norms"]
        self.levels = load_json(os.path.join(DATA, "levels.json"))
        self.policy = load_json(os.path.join(DATA, "policy.json"))
        self.clf = Classifier()
        self.used = set()

    def cite(self, *ids):
        self.used.update(ids)
        return list(ids)

    def F(self, step, title, conclusion, explanation, basis, missing=None):
        return {"step": step, "title": title, "conclusion": conclusion, "explanation": explanation,
                "basis": self.cite(*basis), "missing": missing or []}

    # ------------------------------------------------------------------
    def assess(self, card: dict, find_cases: bool = True) -> dict:
        self.used = set()
        m, c, cu, ob = card["member"], card["contract"], card["customer"], card["object"]
        kind = c.get("kind", "unknown")
        wt = card.get("work_type", "unknown")
        price = effective_price(c)
        proc = c.get("procurement", "unknown")
        findings, missing = [], []
        hard_no, needs, conditional = [], [], []

        # --- 1. Вид договора ------------------------------------------
        if kind in NON_PODRYAD:
            findings.append(self.F(1, "Вид договора", "no",
                f"По содержанию обязательств это {KIND_RU[kind]}: результата работ на объекте капитального строительства подрядчик не создаёт и не сдаёт. "
                f"Обязательное членство в СРО и совокупный размер обязательств относятся только к договорам подряда на изыскания, проектирование, "
                f"строительство, реконструкцию, капитальный ремонт и снос." + (f" Основание в договоре: {c['kind_basis']}." if c.get("kind_basis") else ""),
                KIND_BASIS[kind] + ["grk-52-2.1"]))
            hard_no.append("not_podryad")
        elif kind == "unknown":
            findings.append(self.F(1, "Вид договора", "needs_facts",
                "Вид договора не установлен. Определяется по содержанию: есть ли овеществлённый результат работ, который сдаётся по акту (подряд), "
                "либо передаётся товар (поставка), либо совершаются действия без результата (услуги).",
                ["gk-431", "gk-702", "gk-506", "gk-779"], ["вид договора по предмету и порядку сдачи-приёмки"]))
            needs.append("kind")
        elif kind == "mixed":
            parts = c.get("mixed_parts") or []
            pk = [p["kind"] for p in parts]
            findings.append(self.F(1, "Вид договора", "info",
                "Договор смешанный: " + (", ".join(KIND_RU.get(k, k) for k in pk) if pk else "части не выделены") +
                ". К каждой части применяются правила о соответствующем договоре; членство и совокупный размер определяются по частям-подрядам."
                + (f" Основание: {c['kind_basis']}." if c.get("kind_basis") else ""),
                ["gk-421-3", "gk-431"] + sum((KIND_BASIS.get(k, []) for k in pk), [])))
            if not parts:
                needs.append("mixed_parts")
                missing.append("состав смешанного договора: какие части подряд, какие поставка/услуги, и их цены")
        else:
            findings.append(self.F(1, "Вид договора", "info",
                f"По содержанию обязательств это {KIND_RU[kind]}." + (f" Основание: {c['kind_basis']}." if c.get("kind_basis") else "") +
                (" Пункт 2 ст. 740 ГК РФ распространяет строительный подряд и на монтажные, пусконаладочные и иные неразрывно связанные работы, а также на капитальный ремонт." if kind == "construction" else ""),
                KIND_BASIS[kind]))

        # --- 2. Объект и вид работ ------------------------------------
        obj_basis, obj_expl, obj_conc, obj_missing = ["grk-1-10"], [], "info", []
        if ob.get("is_capital") is False:
            obj_conc = "no"
            obj_expl.append("Объект не является объектом капитального строительства (некапитальное строение, замощение, временное сооружение): работы на нём не относятся к строительству, реконструкции или капитальному ремонту ОКС, членства не требуют и в совокупный размер не входят.")
            obj_basis += ["grk-1-10.2", "grk-52-2.1"]
            hard_no.append("not_capital")
        elif ob.get("is_capital") is None:
            obj_conc = "needs_facts"
            obj_expl.append("Не установлено, является ли объект объектом капитального строительства.")
            obj_missing.append("характер объекта: здание/сооружение (ОКС) или некапитальное строение")
        else:
            obj_expl.append("Объект — объект капитального строительства.")
        ht = ob.get("housing_type", "unknown")
        if ht in HOUSING_EXCLUDED:
            obj_conc = "no"
            obj_expl.append(f"Объект — {HOUSING_RU[ht]}: разрешение на строительство не требуется, Перечень видов работ на такие объекты не распространяется, договор подряда на них членства не требует.")
            obj_basis += ["grk-51-17", "order-624-p2"]
            hard_no.append("housing_excluded")
        elif ht == "unknown" and ob.get("is_capital") is not False:
            obj_missing.append("тип объекта: не ИЖС, не садовый дом, не блокированный/малоэтажный дом, не вспомогательная постройка")
        if wt in ("current_repair", "improvement"):
            obj_conc = "no"
            obj_expl.append(f"Характер работ — {WORK_TYPE_RU[wt]}: это не строительство, не реконструкция и не капитальный ремонт в смысле ГрК РФ (замена или восстановление конструкций, инженерных систем), поэтому договор не является строительным подрядом на ОКС для целей членства.")
            obj_basis += ["grk-1-14.2", "grk-52-2.1"]
            hard_no.append("not_construction_work")
        elif wt in WORK_TYPE_BASIS:
            obj_expl.append(f"Характер работ — {WORK_TYPE_RU[wt]}." + (" Разрешение на строительство для капитального ремонта не требуется, но это работы на объекте капитального строительства: обязательное членство сохраняется." if wt == "capital_repair" else ""))
            obj_basis += WORK_TYPE_BASIS[wt] + (["grk-51-17"] if wt == "capital_repair" else [])
        elif wt == "unknown" and kind in ("construction", "demolition", "mixed", "unknown"):
            obj_missing.append("характер работ: строительство / реконструкция / капитальный ремонт / текущий ремонт / благоустройство")
        cat = ob.get("category", "unknown")
        if cat == "hazardous_48_1":
            obj_expl.append("Объект отнесён к особо опасным, технически сложным или уникальным: работы Перечня со знаком «*» на нём относятся к влияющим на безопасность.")
            obj_basis += ["grk-48.1", "order-624-note"]
        elif cat == "ordinary":
            obj_expl.append("Объект обычный (не ст. 48.1 ГрК РФ): работы Перечня со знаком «*» к влияющим на безопасность не относятся.")
            obj_basis += ["grk-48.1", "order-624-note", "letter-33838"]
        else:
            obj_missing.append("категория объекта по ст. 48.1 ГрК РФ (для работ Перечня со знаком «*»)")
        if ob.get("basis"):
            obj_expl.append(f"Основание: {ob['basis']}.")
        if obj_conc == "info" and obj_missing:
            obj_conc = "needs_facts"
        if obj_conc == "needs_facts":
            needs.append("object")
        missing += obj_missing
        findings.append(self.F(2, "Объект и характер работ", obj_conc, " ".join(obj_expl), obj_basis, obj_missing))

        # --- 3. Стороны ------------------------------------------------
        if m.get("role") != "contractor":
            findings.append(self.F(3, "Стороны договора", "no",
                f"{m['name']} в этом договоре — заказчик. Обязательства по договору несёт её контрагент; для члена СРО это договор субподряда, "
                "который не уведомляется и в его совокупный размер не входит.", ["grk-55.8-4", "grk-52-2.1"]))
            hard_no.append("member_is_customer")
        else:
            ck = cu.get("kind", "unknown")
            base = f"Заказчик — {cu['name']}: {CUSTOMER_RU.get(ck, ck)}." + (f" Основание: {cu['kind_basis']}." if cu.get("kind_basis") else "")
            if ck in QUALIFYING:
                findings.append(self.F(3, "Стороны договора", "yes",
                    base + " Договор подряда с таким заказчиком требует членства подрядчика в СРО и входит в совокупный размер обязательств.",
                    CUSTOMER_BASIS.get(ck, []) + ["grk-52-2.1", "grk-48-4", "grk-47-2"]))
            elif ck in SUBCONTRACT:
                extra = ""
                if c.get("procurement") == "competitive":
                    extra = (" Договор заключён конкурентным способом: по букве ч. 3 ст. 55.8 такой договор конкурентный, но по разъяснению Минстроя "
                             "(письмо № 18965-ОС/02) обязательства перед СРО возникают только по договорам, где членство требуется законом. Практика проверяющего "
                             f"(policy.json): {'не включать, показать отдельной строкой' if self.policy.get('subcontract_competitive') == 'exclude' else 'включать'}.")
                findings.append(self.F(3, "Стороны договора", "no",
                    base + " Заказчик не входит в перечень лиц, договор с которыми требует членства (застройщик, технический заказчик, лицо, ответственное "
                    "за эксплуатацию, региональный оператор): это субподряд. Членства не требует, в совокупный размер не входит." + extra,
                    ["grk-52-2.1", "grk-48-4", "grk-47-2", "minstroy-18965"] + (["grk-55.8-3"] if extra else [])))
                hard_no.append("subcontract")
            elif ck == "individual":
                findings.append(self.F(3, "Стороны договора", "conditional",
                    base + " Физическое лицо является застройщиком, если обеспечивает строительство на своём участке (п. 16 ст. 1 ГрК РФ); для ИЖС, садовых "
                    "домов и вспомогательных построек обязательного членства нет. Нужно установить вид объекта.",
                    ["grk-1-16", "grk-51-17", "order-624-p2"], ["вид объекта у заказчика-физлица"]))
                conditional.append("individual")
            elif ck == "state_entity":
                findings.append(self.F(3, "Стороны договора", "conditional",
                    base + " Государственное или муниципальное учреждение обычно выступает застройщиком либо техническим заказчиком: тогда договор требует "
                    "членства и входит в совокупный размер. Статус заказчика как учреждения освобождает от членства не подрядчика, а само учреждение, "
                    "когда оно выполняет работы своими силами. Нужно подтвердить: разрешение на строительство, контракт, полномочия техзаказчика.",
                    ["grk-1-16", "grk-1-22", "grk-52-2.2", "grk-52-2.1"], ["статус заказчика: застройщик или технический заказчик"]))
                conditional.append("state_customer")
            else:
                findings.append(self.F(3, "Стороны договора", "needs_facts",
                    base + " Нужно установить, застройщик ли это (разрешение на строительство, право на участок, проектная декларация), технический заказчик "
                    "(договор с застройщиком о передаче функций), лицо, ответственное за эксплуатацию, региональный оператор — или иное лицо.",
                    ["grk-1-16", "grk-1-22", "grk-52-2.1"], ["статус заказчика"]))
                needs.append("customer")
                missing.append("статус заказчика (застройщик / технический заказчик / эксплуатант / региональный оператор / иное)")
        if m.get("is_state_entity"):
            findings.append(self.F(3, "Исключение для подрядчика", "no",
                f"{m['name']} — государственная или муниципальная организация из ч. 2.2 ст. 52 ГрК РФ: обязательное членство на неё не распространяется.",
                ["grk-52-2.2"]))
            hard_no.append("member_state_entity")

        # --- 4. Порог и вид СРО ---------------------------------------
        sro_kind = KIND_SRO.get(kind)
        if kind == "mixed":
            pk = {p["kind"] for p in (c.get("mixed_parts") or [])} & PODRYAD
            sro_kind = "mixed" if len({KIND_SRO[k] for k in pk}) > 1 else (KIND_SRO[next(iter(pk))] if pk else None)
        thr = None
        if kind == "construction":
            thr = self.levels["thresholds"]["build_contract_rub"]["value"]
        elif kind == "demolition":
            thr = self.levels["thresholds"]["demolition_contract_rub"]["value"]
        if kind in ("construction", "demolition"):
            if price is None:
                findings.append(self.F(4, "Порог по одному договору", "needs_facts",
                    f"Цена договора не установлена; порог обязательного членства — {money(thr)[:-3]} ₽ по каждому договору с учётом дополнительных соглашений.",
                    ["grk-52-2.1" if kind == "construction" else "grk-55.31-5", "fz-124"], ["цена договора с учётом всех ДС"]))
                needs.append("price")
                missing.append("цена договора с учётом всех дополнительных соглашений")
            elif price <= thr:
                findings.append(self.F(4, "Порог по одному договору", "no",
                    f"Размер обязательств по договору {money(price)} ₽ не превышает {money(thr)[:-3]} ₽: обязательного членства по этому договору нет. "
                    "Включать ли такой договор члена СРО в совокупный размер — определяет положение о контроле конкретной СРО; при консервативном подходе включается. "
                    "Дробление одного объёма работ на договоры ниже порога СРО вправе рассматривать как обход."
                    + (" Договор заключён конкурентным способом: по ч. 3 ст. 55.8 он входит в совокупный размер по КФ ОДО как конкурентный (практика проверяющего: включать)."
                       if (proc == "competitive" and self.policy.get("below_threshold_competitive") == "include") else ""),
                    ["grk-52-2.1" if kind == "construction" else "grk-55.31-5", "fz-124"] + (["grk-55.8-3"] if proc == "competitive" else [])))
                hard_no.append("below_threshold")
            else:
                findings.append(self.F(4, "Порог по одному договору", "yes",
                    f"Размер обязательств по договору {money(price)} ₽ выше порога {money(thr)[:-3]} ₽: обязательное членство в СРО {SRO_RU['build']}.",
                    ["grk-52-2.1" if kind == "construction" else "grk-55.31-5", "fz-124"]))
        elif kind in ("design", "survey"):
            findings.append(self.F(4, "Порог по одному договору", "yes",
                f"Для {'подготовки проектной документации' if kind == 'design' else 'инженерных изысканий'} суммового порога нет: договор с застройщиком или "
                f"техническим заказчиком требует членства в СРО {SRO_RU[sro_kind]} при любой цене" + (f" ({money(price)} ₽)" if price is not None else "") + ".",
                ["grk-48-4" if kind == "design" else "grk-47-2"]))
        elif kind == "mixed":
            parts = c.get("mixed_parts") or []
            cparts = [p for p in parts if p["kind"] in ("construction", "demolition")]
            camt = sum(p.get("amount_rub") or 0 for p in cparts) if cparts and all(p.get("amount_rub") is not None for p in cparts) else None
            if cparts and camt is not None:
                t = self.levels["thresholds"]["build_contract_rub"]["value"]
                conc = "yes" if camt > t else "no"
                findings.append(self.F(4, "Порог по одному договору", conc,
                    f"Строительная часть смешанного договора {money(camt)} ₽ {'выше' if conc == 'yes' else 'не выше'} порога {money(t)[:-3]} ₽."
                    + (" Проектная или изыскательская часть порога не имеет." if any(p['kind'] in ('design', 'survey') for p in parts) else ""),
                    ["gk-421-3", "grk-52-2.1", "grk-48-4", "grk-47-2"]))
                if conc == "no" and not any(p["kind"] in ("design", "survey") for p in parts):
                    hard_no.append("below_threshold")
            else:
                findings.append(self.F(4, "Порог по одному договору", "conditional",
                    "Цены частей смешанного договора не выделены: порог 10 млн ₽ применяется к строительной части, проектная и изыскательская части порога не имеют. "
                    "Пока части не выделены, договор оценивается по полной цене.", ["gk-421-3", "grk-52-2.1", "grk-48-4", "grk-47-2"],
                    ["цены частей смешанного договора"]))
                conditional.append("mixed_price")
                missing.append("цены частей смешанного договора (строительная / проектная / поставка)")

        # --- 5. Совокупный размер (ОДО) --------------------------------
        status = c.get("status", "unknown")
        executed = c.get("executed_rub")
        odo_note = None
        odo_conditional = False
        hard_no_odo = False
        if status == "completed" and c.get("has_final_act"):
            findings.append(self.F(5, "Совокупный размер обязательств", "no",
                "Договор исполнен, результат принят по акту: обязательства, признанные исполненными на основании акта приёмки, в фактический совокупный "
                "размер не включаются. Об исполнении член СРО уведомляет СРО в три рабочих дня." + (f" Основание: {c['status_basis']}." if c.get("status_basis") else ""),
                ["grk-55.13-7", "gk-753", "grk-55.8-4"]))
            hard_no.append("executed")
        elif status == "terminated":
            doc = c.get("termination_document")
            findings.append(self.F(5, "Совокупный размер обязательств", "no" if doc else "needs_facts",
                ("Договор расторгнут (" + doc + "): с даты расторжения обязательств нет; принятые до этого работы — по актам. О расторжении уведомляется СРО.")
                if doc else "Заявлено расторжение, но документ (соглашение о расторжении, уведомление об отказе с датой) не представлен.",
                ["grk-55.8-4", "grk-55.13-7"], [] if doc else ["документ о расторжении договора"]))
            (hard_no if doc else needs).append("terminated")
        else:
            if proc == "competitive":
                findings.append(self.F(5, "Совокупный размер обязательств", "yes",
                    "Договор заключён конкурентным способом: у СРО должен быть сформирован КФ обеспечения договорных обязательств, а совокупный размер "
                    "обязательств члена по таким договорам не должен превышать уровень, за который внесён взнос. Договор входит в совокупный размер по КФ ОДО; "
                    "исполненная по актам часть исключается (ч. 7 ст. 55.13)." + (f" Основание: {c['procurement_basis']}." if c.get("procurement_basis") else ""),
                    ["grk-55.8-3", "grk-55.13-7", "grk-55.16-13" if sro_kind == "build" else "grk-55.16-11", "fz-44", "fz-223"]))
            elif proc == "direct":
                if self.policy.get("odo_scope") == "competitive_only":
                    odo_note = "direct_excluded"
                    findings.append(self.F(5, "Совокупный размер обязательств", "no",
                        "Договор заключён без конкурентных процедур. Совокупный размер обязательств по КФ ОДО считается по договорам, заключённым с использованием "
                        "конкурентных способов (ч. 3 ст. 55.8, ч. 7 ст. 55.13 ГрК РФ в редакции 2026 года): прямой договор в него не входит. "
                        "При этом с 1 марта 2026 года о заключении, изменении, исполнении и расторжении такого договора член СРО уведомляет СРО в три рабочих дня (ч. 4 ст. 55.8)."
                        + (f" Основание: {c['procurement_basis']}." if c.get("procurement_basis") else ""),
                        ["grk-55.8-3", "grk-55.13-7", "grk-55.8-4", "fz-309"]))
                    hard_no_odo = True
                else:
                    odo_note = "two_readings"
                    findings.append(self.F(5, "Совокупный размер обязательств", "conditional",
                        "Договор заключён без конкурентных процедур. По букве ч. 3 ст. 55.8 ГрК РФ совокупный размер считается по договорам, заключённым "
                        "конкурентным способом; практика проверяющего (policy.json) — учитывать все договоры с застройщиком и техзаказчиком.",
                        ["grk-55.8-3", "grk-55.8-4", "fz-309"]))
                    odo_conditional = True
            else:
                findings.append(self.F(5, "Совокупный размер обязательств", "needs_facts",
                    "Способ заключения договора не установлен (торги по 44-ФЗ, 223-ФЗ, конкурентная закупка застройщика — или прямой договор).",
                    ["grk-55.8-3", "fz-309"], ["способ заключения договора"]))
                needs.append("procurement")
                missing.append("способ заключения договора (конкурентный / прямой)")
            if executed is not None and price is not None:
                findings.append(self.F(6, "Исполненная часть", "info",
                    f"Принято по актам {money(executed)} ₽; остаток обязательств {money(max(price - executed, 0))} ₽ — именно он входит в совокупный размер."
                    + (f" Основание: {c['executed_basis']}." if c.get("executed_basis") else ""), ["grk-55.13-7", "gk-753"]))
            elif status == "active":
                missing.append("подписанные акты приёмки (КС-2/КС-3) для расчёта остатка обязательств")

        # --- 6. Виды работ ---------------------------------------------
        works_out, wsum = [], {"total": 0.0, "sro": 0.0, "non": 0.0, "unres": 0.0, "n": 0, "n_sro": 0, "n_non": 0, "n_unres": 0}
        ckind_for_lines = None if kind in ("mixed", "unknown") else kind
        for w in card.get("works", []):
            cl = self.clf.classify_text(w["name"], object_category=cat, contract_kind=ckind_for_lines)
            hd = w.get("human_decision")
            sro = cl["sro"]
            basis = ["order-624"]
            if cl["kind"] == "perechen":
                basis.append("order-624")
                if cl["asterisk"]:
                    basis += ["order-624-note", "grk-48.1"] + (["letter-33838"] if cat == "ordinary" else [])
            elif cl["kind"] == "non_work":
                basis += {"supply": ["gk-506"], "services": ["gk-779"], "rent": ["gk-606"], "overhead": ["gk-740"]}.get(cl.get("category") or "", ["gk-431"])
            elif cl["kind"] == "not_in_list":
                basis += ["fz-372"]
            note = cl.get("note")
            if hd and hd.get("sro") is not None:
                sro = hd["sro"]
                note = "Решение человека: " + (hd.get("note") or "") + (f" (код {hd['perechen_code']})" if hd.get("perechen_code") else "")
            self.used.update(basis)
            amt = w.get("amount_rub")
            row = {"name": w["name"], "amount_rub": r2(amt), "sro": sro, "perechen_code": (hd or {}).get("perechen_code") or cl.get("perechen_code"),
                   "perechen_title": cl.get("perechen_title"), "asterisk": cl.get("asterisk"), "kind": cl["kind"], "reason": cl["reason"],
                   "confidence": 1.0 if hd and hd.get("sro") is not None else cl["confidence"], "note": note, "basis": sorted(set(basis)),
                   "source": w.get("source")}
            works_out.append(row)
            wsum["n"] += 1
            key = {True: "sro", False: "non", None: "unres"}[sro]
            wsum["n_" + key] += 1
            if amt is not None:
                wsum["total"] += amt
                wsum[key] += amt
        share, share_basis = None, None
        if wsum["n"]:
            all_star = all(w["asterisk"] for w in works_out if w["kind"] == "perechen") and any(w["kind"] == "perechen" for w in works_out)
            expl = (f"Видов работ: {wsum['n']}; по Перечню 624 относятся к влияющим на безопасность («СРО»): {wsum['n_sro']}, не относятся: {wsum['n_non']}, "
                    f"не решено: {wsum['n_unres']}. Разделение по Перечню показывает состав цены и не меняет учёт договора: с 01.07.2017 обязанность членства "
                    "и совокупный размер обязательств определяются договором (вид, заказчик, цена, способ заключения), а не видом работ.")
            if all_star and cat == "ordinary":
                expl += (" Все виды работ по договору помечены в Перечне знаком «*», а объект обычный: по классификатору 2010 года такие работы на обычных объектах "
                         "допуска не требовали. Это типичный довод подрядчика; после 372-ФЗ он на учёт договора не влияет.")
            findings.append(self.F(6, "Виды работ по Перечню 624", "info", expl, ["order-624", "fz-372", "grk-52-2.1"] + (["order-624-note", "letter-33838"] if all_star else [])))
            if wsum["total"] > 0 and (wsum["sro"] + wsum["non"]) > 0:
                share = wsum["sro"] / (wsum["sro"] + wsum["non"])
                share_basis = "по стоимости видов работ" + (" (без нерешённых строк)" if wsum["unres"] > 0 else "")
            elif (wsum["n_sro"] + wsum["n_non"]) > 0:
                share = wsum["n_sro"] / (wsum["n_sro"] + wsum["n_non"])
                share_basis = "по числу видов работ — цены не выделены, приближение"
                missing.append("стоимость по видам работ (смета или приложение к договору)")
        else:
            missing.append("перечень видов работ (предмет, смета, приложение) для разделения цены на «СРО / не СРО»")

        # --- Вердикт ----------------------------------------------------
        if hard_no:
            membership = "no"
        elif needs and any(n in ("kind", "object", "customer", "price") for n in needs):
            membership = "needs_facts"
        elif conditional:
            membership = "conditional"
        else:
            membership = "yes"
        below_only = hard_no == ["below_threshold"]
        if "executed" in hard_no or "terminated" in hard_no or hard_no_odo:
            counts = "no"
        elif membership == "no" and not below_only:
            counts = "no"
        elif "procurement" in needs or "terminated" in needs:
            counts = "needs_facts"
        elif below_only:
            if proc == "competitive" and self.policy.get("below_threshold_competitive") == "include":
                counts = "yes"
            elif proc == "competitive":
                counts = "conditional"
            else:
                counts = "no"
        elif membership == "needs_facts":
            counts = "needs_facts"
        elif membership == "conditional" or odo_conditional:
            counts = "conditional"
        else:
            counts = "yes"

        remaining = None if price is None else (0.0 if counts == "no" and ("executed" in hard_no or "terminated" in hard_no) else max(price - (executed or 0), 0.0))
        amount_sro = r2(price * share) if (price is not None and share is not None) else None
        summary = self._summary(card, membership, counts, sro_kind, price, share, remaining, hard_no, odo_conditional)
        verdict = {
            "membership_required": membership, "sro_kind": sro_kind, "counts_for_odo": counts, "odo_note": odo_note,
            "amount_total_rub": r2(price), "amount_sro_rub": amount_sro,
            "amount_non_sro_rub": r2(price - price * share) if (price is not None and share is not None) else None,
            "amount_unresolved_rub": r2(wsum["unres"]) if wsum["unres"] else None,
            "remaining_rub": r2(remaining), "remaining_sro_rub": r2(remaining * share) if (remaining is not None and share is not None) else None,
            "share_sro": None if share is None else round(share, 4), "share_basis": share_basis,
            "confidence": self._confidence(card, needs, conditional, works_out), "summary": summary,
        }
        precedents = []
        if find_cases:
            try:
                from cases import find_similar, features_from_card
                precedents = find_similar(features_from_card(card, verdict), limit=3)
            except Exception as e:  # база прецедентов необязательна
                precedents = [{"error": str(e)}]
        law_index = {i: self.law[i] for i in sorted(self.used) if i in self.law}
        seen, mlist = set(), []
        for x in missing:
            if x not in seen:
                seen.add(x)
                mlist.append(x)
        return {
            "schema_version": "1",
            "contract_ref": {"member": m["name"], "role": m["role"], "number": c["number"], "date": c.get("date"), "customer": cu["name"],
                             "customer_kind": cu.get("kind"), "kind": kind, "work_type": wt, "price_rub": r2(price), "price_band": price_band(price),
                             "procurement": proc, "status": status, "object": ob["name"], "object_category": cat, "as_of": card.get("as_of")},
            "verdict": verdict, "findings": findings, "works": works_out, "missing_facts": mlist, "precedents": precedents,
            "law_index": law_index,
            "verification_note": "Нормы приведены по реестру scripts/data/law.json без сверки с официальным текстом (сеть среды закрыта). Перед использованием в споре сверить формулировки и номера частей.",
        }

    def _confidence(self, card, needs, conditional, works):
        conf = 0.9
        conf -= 0.2 * len(needs)
        conf -= 0.1 * len(conditional)
        if works:
            conf -= 0.1 * (sum(1 for w in works if w["sro"] is None) / len(works))
        ec = [s.get("extraction_confidence") for s in card.get("sources", []) if s.get("extraction_confidence") is not None]
        if ec:
            conf = min(conf, min(ec) + 0.1)
        return round(max(0.05, min(conf, 0.95)), 2)

    def _summary(self, card, membership, counts, sro_kind, price, share, remaining, hard_no, odo_conditional):
        c = card["contract"]
        who = card["member"]["name"]
        p = f"{money(price)} ₽" if price is not None else "цена не установлена"
        if membership == "no":
            why = {"not_podryad": "договор не является договором подряда", "not_capital": "объект не является объектом капитального строительства",
                   "housing_excluded": "объект выведен из-под обязательного членства (ИЖС и приравненные)", "not_construction_work": "работы не являются строительством, реконструкцией или капитальным ремонтом",
                   "member_is_customer": f"{who} в договоре — заказчик", "subcontract": "заказчик не застройщик и не технический заказчик (субподряд)",
                   "member_state_entity": "подрядчик подпадает под исключение ч. 2.2 ст. 52 ГрК РФ", "below_threshold": "цена не выше порога обязательного членства",
                   "executed": "договор исполнен и принят по акту", "terminated": "договор расторгнут"}
            reasons = "; ".join(why[h] for h in hard_no if h in why)
            if counts == "yes":
                return (f"Договор № {c['number']} ({p}) обязательного членства в СРО не требует ({reasons}), но как заключённый конкурентным способом "
                        f"входит в совокупный размер обязательств по КФ ОДО (ч. 3 ст. 55.8 ГрК РФ)." + (f" Остаток обязательств {money(remaining)} ₽." if remaining is not None else ""))
            tail = " Включение в совокупный размер — по положению СРО." if counts == "conditional" else ""
            return f"Договор № {c['number']} ({p}) обязательного членства в СРО не требует и в совокупный размер обязательств не входит: {reasons}.{tail}"
        if membership == "needs_facts":
            return f"По договору № {c['number']} ({p}) вывод невозможен без установления фактов, перечисленных ниже."
        kind_ru = SRO_RU.get(sro_kind, "")
        s = f"Договор № {c['number']} ({p}) требует членства в СРО {kind_ru}"
        s += " при условиях, указанных в разборе." if membership == "conditional" else "."
        if counts == "yes":
            s += " Он входит в совокупный размер обязательств по КФ ОДО (конкурентный договор, ч. 3 ст. 55.8 ГрК РФ)."
        elif counts == "no":
            s += " В совокупный размер обязательств по КФ ОДО он не входит: заключён без конкурентных процедур (ч. 3 ст. 55.8 ГрК РФ); уведомлению в СРО подлежит (ч. 4 ст. 55.8)."
        elif counts == "conditional":
            s += " Включение в совокупный размер по КФ ОДО зависит от прочтения ч. 3 ст. 55.8 ГрК РФ после 309-ФЗ и положения СРО (прямой договор)." if odo_conditional else " Включение в совокупный размер — при подтверждении условий."
        elif counts == "needs_facts":
            s += " Для вывода о совокупном размере не хватает фактов."
        if remaining is not None:
            s += f" Остаток обязательств {money(remaining)} ₽"
            if share is not None:
                s += f"; справочно по Перечню 624 из них работы, влияющие на безопасность, — {money(remaining * share)} ₽ ({share * 100:.0f} %)"
            s += "."
        return s


# ---- Markdown ----------------------------------------------------------
CONC_RU = {"yes": "да", "no": "нет", "conditional": "условно", "needs_facts": "нужно установить", "info": "—"}


fmt = money


def markdown(a: dict) -> str:
    law = a["law_index"]
    r = a["contract_ref"]
    v = a["verdict"]

    def cites(ids):
        return "; ".join(law[i]["cite"] for i in ids if i in law)

    proc_ru = {"competitive": "конкурентный", "direct": "прямой", "unknown": "не установлен"}[r["procurement"]]
    out = [f"# Заключение по договору № {r['number']}" + (f" от {r['date']}" if r.get("date") else ""),
           f"Подрядчик (член СРО): **{r['member']}** · Заказчик: **{r['customer']}** ({CUSTOMER_RU.get(r['customer_kind'], r['customer_kind'])}) · "
           f"Объект: {r['object']} · Цена: {fmt(r['price_rub'])} ₽ · Способ заключения: {proc_ru}",
           "", "## Вывод", "",
           f"- **Обязательное членство в СРО:** {CONC_RU[v['membership_required']]}" + (f" (СРО {SRO_RU.get(v['sro_kind'], '')})" if v.get("sro_kind") else ""),
           f"- **Входит в совокупный размер обязательств (КФ ОДО):** {CONC_RU[v['counts_for_odo']]}",
           f"- **Остаток обязательств по договору:** {fmt(v['remaining_rub'])} ₽" + (" — эта сумма идёт в совокупный размер" if v['counts_for_odo'] == 'yes' else ""),
           f"- **Справочно, по Перечню 624:** работы, влияющие на безопасность, — {fmt(v['remaining_sro_rub'])} ₽ из остатка"
           + (f" ({v['share_sro'] * 100:.1f} %, {v['share_basis']})".replace(".", ",") if v.get("share_sro") is not None else " (виды работ не разобраны)"),
           f"- **Уверенность:** {v['confidence']:.2f}", "", v["summary"], "", "## Разбор по шагам", ""]
    for f in a["findings"]:
        out.append(f"### {f['step']}. {f['title']}" + (f" — {CONC_RU[f['conclusion']]}" if f['conclusion'] != 'info' else ""))
        out.append(f["explanation"])
        if f["basis"]:
            out.append(f"*Основание:* {cites(f['basis'])}.")
        if f.get("missing"):
            out.append("*Нужно установить:* " + "; ".join(f["missing"]) + ".")
        out.append("")
    if a["works"]:
        out += ["## Виды работ: что относится к СРО, что нет", "",
                "| Вид работ | Сумма, ₽ | Итог | Перечень 624 | Основание |", "|---|---:|---|---|---|"]
        for w in a["works"]:
            t = {True: "**СРО**", False: "не СРО", None: "решает человек"}[w["sro"]]
            code = (w.get("perechen_code") or "—") + (" *" if w.get("asterisk") else "")
            out.append(f"| {w['name']} | {fmt(w['amount_rub'])} | {t} | {code} | {w['reason']} — {cites(w['basis'])} |")
        out.append("")
    if a["missing_facts"]:
        out += ["## Что нужно установить для окончательного вывода", ""] + [f"- {x}" for x in a["missing_facts"]] + [""]
    if a["precedents"] and not a["precedents"][0].get("error"):
        out += ["## Похожие прецеденты из базы", ""]
        for p in a["precedents"]:
            out.append(f"- {p['id']} ({p['date']}, сходство {p['score']:.2f}): {p['human_decision']}" + (f" — {p['note']}" if p.get("note") else ""))
        out.append("")
    out += ["## Нормы, на которые опирается заключение", ""]
    for i, n in law.items():
        out.append(f"- **{n['cite']}** — {n['gist']}")
    out += ["", f"> {a['verification_note']}"]
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("card")
    ap.add_argument("-o", "--out")
    ap.add_argument("--md")
    ap.add_argument("--no-cases", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    card = load_json(args.card)
    a = Assessor().assess(card, find_cases=not args.no_cases)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(a, f, ensure_ascii=False, indent=2)
            f.write("\n")
    md = markdown(a)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(md)
    if not args.quiet:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
