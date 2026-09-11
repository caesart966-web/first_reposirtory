#!/usr/bin/env python3
"""Расчёт обязательств члена СРО по реестру: что в расчёт, что нет, сколько.

Обычная арифметика по размеченному реестру (после classify.py). Скрипт НЕ
выносит вердикт «превышение»: он выдаёт суммы — цену договоров, часть, которая
относится к СРО, выполненное по актам и остаток — по каждому виду СРО
(строительство / проектирование / изыскания) в двух выборках:
  • all_qualifying  — все договоры подряда с застройщиком, техзаказчиком,
    эксплуатирующей организацией, региональным оператором (ч. 2.1 ст. 52,
    ч. 4.1 ст. 48, ч. 2.1 ст. 47 ГрК РФ), где проверяемая компания — подрядчик;
  • competitive_only — из них заключённые конкурентным способом (буква
    ч. 3 ст. 55.8 ГрК РФ).
Уровень ответственности, покрывающий сумму, приводится справочно.

Использование:
    python3 odo.py register.json -o result.json [--md summary.md]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

QUALIFYING = {"developer", "technical_customer", "operator", "regional_operator"}
PODRYAD = {"construction", "demolition", "design", "survey", "mixed"}
KIND_TO_SRO = {"construction": "build", "demolition": "build", "design": "design", "survey": "survey"}
DEFAULT_CALC_ROLE = {"ks2": "executed", "upd": "executed", "act": "executed", "estimate": "price_split"}
SRO_KINDS = ("build", "design", "survey")
KIND_LABEL = {"build": "строительство", "design": "проектирование", "survey": "изыскания"}
CTR_KIND = {"construction": "строительный подряд", "demolition": "снос", "design": "проектирование", "survey": "изыскания",
            "mixed": "смешанный", "supply": "поставка", "services": "услуги", "other": "иное"}
PROC = {"competitive": "конкурентный", "direct": "прямой", "unknown": "не указан"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def r2(x):
    return None if x is None else round(float(x), 2)


def line_amount(li, doc, basis):
    """Сумма строки в выбранном базисе; если нет — довести по ставке документа."""
    w, wo = li.get("amount_with_vat_rub"), li.get("amount_rub")
    if basis == "with_vat":
        if w is not None:
            return float(w), None
        if wo is not None:
            k = _vat_factor(doc)
            return float(wo) * k, ("с НДС доведено по ставке документа" if k != 1 else "в документе без НДС")
        return 0.0, "нет суммы"
    else:
        if wo is not None:
            return float(wo), None
        if w is not None:
            k = _vat_factor(doc)
            return float(w) / k, ("без НДС доведено по ставке документа" if k != 1 else None)
        return 0.0, "нет суммы"


def _vat_factor(doc):
    a, b = doc.get("amount_with_vat_rub"), doc.get("amount_without_vat_rub")
    if a and b and b > 0:
        return float(a) / float(b)
    rate = (doc.get("vat_rate") or "").replace("%", "").replace(",", ".").strip()
    try:
        return 1 + float(rate) / 100 if rate else 1.0
    except ValueError:
        return 1.0


def contract_applicability(c, thresholds):
    """Считается ли договор в совокупный размер обязательств и почему."""
    reasons, flags = [], []
    counts = True
    if c.get("role") != "contractor":
        counts = False
        reasons.append("проверяемая компания в этом договоре — заказчик; это обязательства её контрагента (субподряд), справочно")
    if c.get("kind") not in PODRYAD:
        counts = False
        reasons.append(f"не договор подряда на изыскания/проектирование/строительство/снос (вид: {c.get('kind')})")
    ck = (c.get("counterparty") or {}).get("kind", "unknown")
    if counts:
        if ck in QUALIFYING:
            reasons.append("заказчик из перечня ч. 2.1 ст. 52 / ч. 4.1 ст. 48 / ч. 2.1 ст. 47 ГрК РФ — договор входит")
        elif ck == "unknown":
            flags.append("counterparty_unknown")
            reasons.append("статус заказчика не подтверждён — включено условно, требуется подтверждение")
        else:
            counts = False
            reasons.append("заказчик не застройщик/техзаказчик/эксплуатант/региональный оператор: субподряд, членство не требуется, в совокупный размер не входит (ч. 2.1 ст. 52 ГрК РФ; статья о 309-ФЗ)")
    price = c.get("price_rub")
    if counts and price is not None:
        thr = None
        if c.get("kind") == "construction":
            thr = thresholds["build_contract_rub"]["value"]
        elif c.get("kind") == "demolition":
            thr = thresholds["demolition_contract_rub"]["value"]
        if thr and price <= thr:
            flags.append("below_threshold")
            reasons.append(f"цена не выше порога {thr:,.0f} ₽ — членство по этому договору не требуется; в сумме показан, отдельно помечен".replace(",", " "))
    if counts and price is None:
        flags.append("price_unknown")
        reasons.append("цена договора не установлена — остаток не считается")
    if c.get("procurement") == "unknown" and counts:
        flags.append("procurement_unknown")
    if c.get("status") == "completed":
        reasons.append("договор исполнен — обязательства, признанные исполненными по актам, в расчёт не входят (ч. 4 ст. 55.13 ГрК РФ)")
    return counts, reasons, flags


def level_for(amount, table):
    for row in table:
        if row["limit_rub"] is None or amount <= row["limit_rub"]:
            return row
    return table[-1]


def compute(reg: dict, levels: dict) -> dict:
    settings = reg.get("settings") or {}
    basis = settings.get("vat_basis", "with_vat")
    docs = {d["id"]: d for d in reg.get("documents", [])}
    objs = {o["id"]: o for o in reg.get("objects", [])}
    warnings, review = [], []

    # --- группировка строк по договорам ----------------------------------
    by_ctr = defaultdict(lambda: {"executed": [], "price_split": []})
    for li in reg.get("line_items", []):
        if li.get("is_summary"):
            continue
        doc = docs.get(li["document_id"])
        if doc is None:
            warnings.append(f"{li['id']}: документ {li['document_id']} не найден")
            continue
        role = doc.get("calc_role") or DEFAULT_CALC_ROLE.get(doc["kind"], "reference")
        if role == "reference":
            continue
        cid = li.get("contract_id") or doc.get("contract_id")
        if not cid:
            warnings.append(f"{li['id']}: строка без договора")
            continue
        amt, note = line_amount(li, doc, basis)
        if note == "нет суммы":
            warnings.append(f"{li['id']}: нет суммы")
        cl = li.get("classification") or {}
        by_ctr[cid][role].append({
            "id": li["id"], "name": li["name"], "amount": amt, "sro": cl.get("sro"),
            "sro_kind": cl.get("sro_kind"), "code": cl.get("perechen_code"),
            "reason": cl.get("reason"), "review_status": cl.get("review_status"),
            "confidence": cl.get("confidence"), "document_id": doc["id"], "doc_number": doc.get("number"),
            "doc_kind": doc["kind"],
        })
        if cl.get("review_status") == "pending":
            review.append({"type": "line_item", "ref": li["id"], "contract_id": cid,
                           "message": f"«{li['name'][:80]}»: {cl.get('reason', 'не классифицировано')}",
                           "amount": r2(amt)})

    def sums(rows):
        s = {"total": 0.0, "sro": 0.0, "non_sro": 0.0, "unresolved": 0.0, "by_kind": defaultdict(float)}
        for r in rows:
            s["total"] += r["amount"]
            if r["sro"] is True:
                s["sro"] += r["amount"]
                s["by_kind"][r["sro_kind"] or "build"] += r["amount"]
            elif r["sro"] is False:
                s["non_sro"] += r["amount"]
            else:
                s["unresolved"] += r["amount"]
        s["by_kind"] = dict(s["by_kind"])
        return s

    contracts_out = []
    totals = {cut: {k: {"contracts": 0, "price": 0.0, "price_sro": 0.0, "executed": 0.0, "executed_sro": 0.0,
                        "remaining": 0.0, "remaining_sro": 0.0, "unresolved": 0.0,
                        "price_unsplit": 0.0, "remaining_unsplit": 0.0}
                    for k in SRO_KINDS} for cut in ("all_qualifying", "competitive_only")}
    excluded = []

    for c in reg.get("contracts", []):
        counts, reasons, flags = contract_applicability(c, levels["thresholds"])
        sro_kind = c.get("sro_kind") or KIND_TO_SRO.get(c.get("kind"))
        obj = objs.get(c.get("object_id") or "") or {}
        if obj and obj.get("category") == "unknown" and counts:
            review.append({"type": "object", "ref": obj["id"], "contract_id": c["id"],
                           "message": f"Категория объекта «{obj['name']}» не задана (ст. 48.1 ГрК РФ): работы со звёздочкой не решены"})
        if "counterparty_unknown" in flags:
            review.append({"type": "contract", "ref": c["id"], "contract_id": c["id"],
                           "message": f"Договор {c['number']}: статус заказчика «{c['counterparty']['name']}» не подтверждён"})
        if "procurement_unknown" in flags:
            review.append({"type": "contract", "ref": c["id"], "contract_id": c["id"],
                           "message": f"Договор {c['number']}: способ заключения не указан (конкурентный/прямой)"})

        rows = by_ctr.get(c["id"], {"executed": [], "price_split": []})
        ex = sums(rows["executed"])
        ps = sums(rows["price_split"])
        price = c.get("price_rub") if basis == "with_vat" else (c.get("price_without_vat_rub") or c.get("price_rub"))
        for a in c.get("addenda") or []:
            if a.get("price_rub") is not None and basis == "with_vat":
                price = a["price_rub"]

        # Доля СРО в цене: по смете, иначе по актам.
        share, share_basis, share_by_kind = None, None, {}
        ps_resolved = ps["sro"] + ps["non_sro"]
        ex_resolved = ex["sro"] + ex["non_sro"]
        if ps_resolved > 0:
            share = ps["sro"] / ps_resolved
            share_basis = "по смете"
            share_by_kind = {k: v / ps_resolved for k, v in ps["by_kind"].items()}
            if ps["unresolved"] > 0:
                share_basis += f" (не решено {ps['unresolved']:,.0f} ₽ — доля считается по решённым строкам)".replace(",", " ")
        elif ex_resolved > 0:
            share = ex["sro"] / ex_resolved
            share_basis = "по актам (сметы нет: доля выполненного перенесена на остаток — приближение)"
            share_by_kind = {k: v / ex_resolved for k, v in ex["by_kind"].items()}
            if counts:
                review.append({"type": "contract", "ref": c["id"], "contract_id": c["id"],
                               "message": f"Договор {c['number']}: сметы нет, доля СРО в остатке оценена по актам"})
        elif counts:
            share_basis = ("выполненное не разделено (строки не решены)" if ex["total"] > 0
                           else "нет ни сметы, ни актов — цена показана без разделения")
            review.append({"type": "contract", "ref": c["id"], "contract_id": c["id"],
                           "message": f"Договор {c['number']}: нет решённых строк для разделения цены на СРО/не СРО — остаток показан без разделения"})

        executed_total = ex["total"]
        remaining = None
        if price is not None:
            remaining = 0.0 if c.get("status") == "completed" else max(float(price) - executed_total, 0.0)
            if float(price) < executed_total:
                warnings.append(f"Договор {c['number']}: выполнено по актам ({executed_total:,.2f}) больше цены ({float(price):,.2f}) — проверить цену/ДС")
        price_sro = float(price) * share if (price is not None and share is not None) else None
        remaining_sro = remaining * share if (remaining is not None and share is not None) else None

        rec = {
            "id": c["id"], "number": c["number"], "date": c.get("date"), "subject": c.get("subject"),
            "kind": c.get("kind"), "sro_kind": sro_kind, "role": c.get("role"),
            "counterparty": c.get("counterparty"), "procurement": c.get("procurement"),
            "status": c.get("status"), "object": obj.get("name"), "object_category": obj.get("category"),
            "counts_for_odo": counts, "reasons": reasons, "flags": flags,
            "price": r2(price), "price_sro": r2(price_sro), "price_non_sro": r2(float(price) - price_sro) if price_sro is not None else None,
            "share_sro": None if share is None else round(share, 4), "share_basis": share_basis,
            "share_by_kind": {k: round(v, 4) for k, v in share_by_kind.items()},
            "executed": {"total": r2(ex["total"]), "sro": r2(ex["sro"]), "non_sro": r2(ex["non_sro"]),
                          "unresolved": r2(ex["unresolved"]), "by_kind": {k: r2(v) for k, v in ex["by_kind"].items()},
                          "lines": len(rows["executed"])},
            "estimate": {"total": r2(ps["total"]), "sro": r2(ps["sro"]), "non_sro": r2(ps["non_sro"]),
                          "unresolved": r2(ps["unresolved"]), "lines": len(rows["price_split"])},
            "remaining": r2(remaining), "remaining_sro": r2(remaining_sro),
            "remaining_non_sro": r2(remaining - remaining_sro) if remaining_sro is not None else None,
            "lines": rows["executed"] + rows["price_split"],
        }
        contracts_out.append(rec)

        if not counts:
            excluded.append({"id": c["id"], "number": c["number"], "counterparty": c["counterparty"]["name"],
                             "price": r2(price), "reasons": reasons})
            continue
        cuts = ["all_qualifying"] + (["competitive_only"] if c.get("procurement") == "competitive" else [])
        kinds = share_by_kind
        for cut in cuts:
            for k in SRO_KINDS:
                if k != sro_kind and k not in kinds:
                    continue
                t = totals[cut][k]
                if k == sro_kind:
                    t["contracts"] += 1
                    t["price"] += float(price or 0)
                    t["executed"] += ex["total"]
                    t["remaining"] += remaining or 0.0
                    t["unresolved"] += ex["unresolved"]
                    if share is None:
                        t["price_unsplit"] += float(price or 0)
                        t["remaining_unsplit"] += remaining or 0.0
                kshare = kinds.get(k, 0.0)
                t["price_sro"] += float(price or 0) * kshare
                t["executed_sro"] += ex["by_kind"].get(k, 0.0)
                t["remaining_sro"] += (remaining or 0.0) * kshare

    # Округление итогов и справочные уровни.
    hints = {}
    for cut in totals:
        for k in SRO_KINDS:
            totals[cut][k] = {kk: (r2(v) if isinstance(v, float) else v) for kk, v in totals[cut][k].items()}
    for k in SRO_KINDS:
        t = totals["all_qualifying"][k]
        if t["contracts"] == 0:
            continue
        table = levels["odo"][k]["levels"]
        hints[k] = {
            "law": levels["odo"][k]["law"],
            "remaining_sro": t["remaining_sro"],
            "level_covering_remaining_sro": level_for(t["remaining_sro"], table)["level"],
            "level_covering_remaining_total": level_for(t["remaining"], table)["level"],
            "level_covering_price_sro": level_for(t["price_sro"], table)["level"],
            "declared_level": next((s.get("odo_level") for s in reg["subject"].get("sro", []) if s["kind"] == k), None),
            "note": "Справочно: уровень, минимально покрывающий сумму по таблице ст. 55.16 ГрК РФ. Вердикт о соответствии выносит человек по данным реестра СРО.",
        }

    seen, dedup = set(), []
    for r in review:
        key = (r["type"], r["ref"], r["message"])
        if key not in seen:
            seen.add(key)
            dedup.append(r)
    review = dedup

    return {
        "subject": reg["subject"], "as_of": reg.get("as_of"),
        "settings": {"vat_basis": basis, "odo_basis": "цена договора − выполнено по актам (ч. 4 ст. 55.13 ГрК РФ)"},
        "method_notes": [
            "Строка идёт в «СРО», если её вид работ есть в Перечне 624 без звёздочки, либо со звёздочкой на объекте ст. 48.1 ГрК РФ.",
            "Строка идёт в «не СРО», если работ нет в Перечне 624 (отделка, благоустройство, уборка), либо это не работы (поставка, аренда, охрана, накладные, ФОТ), либо звёздочка на обычном объекте.",
            "Договор входит в совокупный размер, если компания — подрядчик по договору подряда с застройщиком, техзаказчиком, эксплуатирующей организацией или региональным оператором. Субподряд не входит.",
            "Выборка competitive_only — буква ч. 3 ст. 55.8 ГрК РФ (конкурентные способы); all_qualifying — все подходящие договоры. 309-ФЗ с 01.03.2026 расширил уведомления на все договоры; какая выборка применяется вашей СРО — уточняется по её положению о контроле.",
        ],
        "contracts": contracts_out, "totals": totals, "excluded": excluded,
        "levels_hint": hints, "review_queue": review, "warnings": warnings,
    }


def fmt(x):
    if x is None:
        return "—"
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")


def markdown(res: dict) -> str:
    s = res["subject"]
    out = [f"# Обязательства члена СРО: {s['name']}" + (f" (ИНН {s['inn']})" if s.get("inn") else ""),
           f"Дата расчёта: {res['as_of']}. Базис: {'с НДС' if res['settings']['vat_basis'] == 'with_vat' else 'без НДС'}. "
           f"Остаток = {res['settings']['odo_basis']}.", ""]
    for cut, title in (("all_qualifying", "Все договоры с застройщиком/техзаказчиком/эксплуатантом/региональным оператором"),
                       ("competitive_only", "Только заключённые конкурентным способом")):
        out.append(f"## {title}")
        out.append("| Вид СРО | Договоров | Цена всего | из них СРО | Выполнено | из них СРО | Остаток всего | Остаток СРО | Остаток не разделён | Выполнено не решено |")
        out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for k in SRO_KINDS:
            t = res["totals"][cut][k]
            if t["contracts"] == 0:
                continue
            out.append(f"| {KIND_LABEL[k]} | {t['contracts']} | {fmt(t['price'])} | {fmt(t['price_sro'])} | {fmt(t['executed'])} | "
                       f"{fmt(t['executed_sro'])} | {fmt(t['remaining'])} | {fmt(t['remaining_sro'])} | {fmt(t['remaining_unsplit'])} | {fmt(t['unresolved'])} |")
        out.append("")
    if res["levels_hint"]:
        out.append("## Справочно: уровень ответственности, покрывающий сумму (ст. 55.16 ГрК РФ)")
        for k, h in res["levels_hint"].items():
            out.append(f"- {KIND_LABEL[k]}: остаток СРО {fmt(h['remaining_sro'])} ₽ → уровень {h['level_covering_remaining_sro']}; "
                       f"остаток без разделения → уровень {h['level_covering_remaining_total']}; заявленный уровень: {h['declared_level'] or '—'}")
        out.append("")
    out.append("## Договоры")
    out.append("| № | Договор | Контрагент | Вид | Способ | В расчёт | Цена | Выполнено | Выполнено СРО | Остаток | Остаток СРО | Доля СРО |")
    out.append("|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|")
    for i, c in enumerate(res["contracts"], 1):
        share = "—" if c["share_sro"] is None else f"{c['share_sro'] * 100:.1f}% ({c['share_basis']})"
        out.append(f"| {i} | {c['number']} от {c['date'] or '—'} | {c['counterparty']['name']} | {CTR_KIND.get(c['kind'], c['kind'])} | {PROC.get(c['procurement'], c['procurement'])} | "
                   f"{'да' if c['counts_for_odo'] else 'нет'} | {fmt(c['price'])} | {fmt(c['executed']['total'])} | {fmt(c['executed']['sro'])} | "
                   f"{fmt(c['remaining'])} | {fmt(c['remaining_sro'])} | {share} |")
    out.append("")
    if res["excluded"]:
        out.append("## Не в расчёте")
        for e in res["excluded"]:
            out.append(f"- {e['number']} ({e['counterparty']}, {fmt(e['price'])} ₽): " + "; ".join(e["reasons"]))
        out.append("")
    if res["review_queue"]:
        out.append(f"## На проверку человеку ({len(res['review_queue'])})")
        for r in res["review_queue"][:100]:
            out.append(f"- [{r['type']}] {r['message']}" + (f" — {fmt(r['amount'])} ₽" if r.get("amount") else ""))
        out.append("")
    if res["warnings"]:
        out.append("## Предупреждения")
        out.extend(f"- {w}" for w in res["warnings"])
        out.append("")
    out.append("## Методика")
    out.extend(f"- {n}" for n in res["method_notes"])
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("register")
    ap.add_argument("-o", "--out", help="result.json")
    ap.add_argument("--md", help="записать сводку в Markdown")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    reg = load_json(args.register)
    levels = load_json(os.path.join(DATA, "levels.json"))
    res = compute(reg, levels)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
            f.write("\n")
    md = markdown(res)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(md)
    if not args.quiet:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
