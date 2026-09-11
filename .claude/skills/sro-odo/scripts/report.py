#!/usr/bin/env python3
"""Отчёт проверяющему: HTML из result.json (выход odo.py).

    python3 report.py result.json -o report.html [--register register.json]

Одностраничный HTML без внешних зависимостей, печатается на А4. Реестр нужен
только для ссылок на страницы документов; без него отчёт тоже строится.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys

KIND_LABEL = {"build": "строительство", "design": "проектирование", "survey": "изыскания"}
CTR_KIND = {"construction": "строительный подряд", "demolition": "снос", "design": "проектирование",
            "survey": "изыскания", "mixed": "смешанный", "supply": "поставка", "services": "услуги", "other": "иное"}
CP_KIND = {"developer": "застройщик", "technical_customer": "технический заказчик", "operator": "эксплуатирующая организация",
           "regional_operator": "региональный оператор", "general_contractor": "генподрядчик", "contractor": "подрядчик",
           "other": "иное лицо", "unknown": "не подтверждено"}
PROC = {"competitive": "конкурентный", "direct": "прямой", "unknown": "не указан"}
STATUS = {"active": "действует", "completed": "исполнен", "terminated": "расторгнут", "unknown": "не указан"}
CAT = {"ordinary": "обычный объект", "hazardous_48_1": "объект ст. 48.1 ГрК РФ", "unknown": "категория не задана"}
DOC_KIND = {"contract": "Договор", "addendum": "ДС", "estimate": "Смета", "ks2": "КС-2", "ks3": "КС-3", "upd": "УПД",
            "invoice": "Счёт-фактура", "act": "Акт", "notification": "Уведомление в СРО", "other": "Документ"}

CSS = """
:root{--ink:#171310;--muted:#6b645c;--line:#d9d2c5;--paper:#fff;--warm:#f6f3ec;--seal:#B0202B;--ok:#2e6b3a}
*{box-sizing:border-box}body{margin:0;padding:24px 16px;font:14px/1.45 "Golos Text",system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--paper)}
main{max-width:1100px;margin:0 auto}h1{font:600 26px/1.2 Literata,Georgia,serif;margin:0 0 6px}h2{font:600 19px/1.25 Literata,Georgia,serif;margin:28px 0 10px;padding-top:12px;border-top:1px solid var(--line)}
h3{font:600 15px/1.3 Literata,Georgia,serif;margin:18px 0 6px}.muted{color:var(--muted)}.small{font-size:12px}
.disclaimer{background:var(--warm);border-left:3px solid var(--seal);padding:10px 14px;margin:14px 0}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{font-weight:600;background:var(--warm)}td.num,th.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.wrap{overflow-x:auto}.tag{display:inline-block;padding:1px 7px;border-radius:3px;font-size:12px;border:1px solid var(--line)}
.tag.yes{border-color:var(--ok);color:var(--ok)}.tag.no{border-color:var(--muted);color:var(--muted)}.tag.q{border-color:var(--seal);color:var(--seal)}
.kpi{display:flex;flex-wrap:wrap;gap:12px;margin:10px 0}.kpi div{flex:1 1 200px;border:1px solid var(--line);padding:10px 12px}
.kpi b{display:block;font-size:20px;font-variant-numeric:tabular-nums}.kpi span{color:var(--muted);font-size:12px}
ul{padding-left:20px}li{margin:3px 0}@media print{body{padding:0}h2{break-after:avoid}tr{break-inside:avoid}}
"""


def fmt(x):
    if x is None:
        return "—"
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")


def esc(x):
    return html.escape("" if x is None else str(x))


def tag(cls, text):
    return f'<span class="tag {cls}">{esc(text)}</span>'


def totals_table(t):
    rows = []
    for k in ("build", "design", "survey"):
        r = t[k]
        if r["contracts"] == 0:
            continue
        rows.append(f"<tr><td>{KIND_LABEL[k]}</td><td class=num>{r['contracts']}</td><td class=num>{fmt(r['price'])}</td>"
                    f"<td class=num><b>{fmt(r['price_sro'])}</b></td><td class=num>{fmt(r['executed'])}</td><td class=num>{fmt(r['executed_sro'])}</td>"
                    f"<td class=num>{fmt(r['remaining'])}</td><td class=num><b>{fmt(r['remaining_sro'])}</b></td><td class=num>{fmt(r['remaining_unsplit'])}</td><td class=num>{fmt(r['unresolved'])}</td></tr>")
    if not rows:
        return "<p class=muted>Подходящих договоров нет.</p>"
    return ("<div class=wrap><table><thead><tr><th>Вид СРО</th><th class=num>Договоров</th><th class=num>Цена всего</th><th class=num>из них СРО</th>"
            "<th class=num>Выполнено</th><th class=num>из них СРО</th><th class=num>Остаток всего</th><th class=num>Остаток СРО</th><th class=num>Остаток не разделён</th><th class=num>Выполнено не решено</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def contract_block(c, docs_by_id):
    cp = c["counterparty"]
    head = (f"<h3>{esc(c['number'])} от {esc(c['date'] or '—')} — {esc(cp['name'])}</h3>"
            f"<p class=small>{esc(c['subject'])}</p>"
            f"<p class=small>{tag('yes' if c['counts_for_odo'] else 'no', 'в расчёт' if c['counts_for_odo'] else 'не в расчёте')} "
            f"{tag('', CTR_KIND.get(c['kind'], c['kind']))} {tag('', 'вид СРО: ' + KIND_LABEL.get(c['sro_kind'], '—'))} "
            f"{tag('', 'заказчик: ' + CP_KIND.get(cp['kind'], cp['kind']))} {tag('', 'способ: ' + PROC.get(c['procurement'], c['procurement']))} "
            f"{tag('', STATUS.get(c['status'], c['status']))} {tag('', CAT.get(c['object_category'] or 'unknown', ''))}</p>"
            "<ul class=small>" + "".join(f"<li>{esc(r)}</li>" for r in c["reasons"]) + "</ul>")
    share = "—" if c["share_sro"] is None else f"{c['share_sro'] * 100:.1f} % ({esc(c['share_basis'])})"
    kpi = (f"<div class=kpi><div><b>{fmt(c['price'])}</b><span>цена договора</span></div>"
           f"<div><b>{fmt(c['price_sro'])}</b><span>из них СРО (доля {share})</span></div>"
           f"<div><b>{fmt(c['executed']['total'])}</b><span>выполнено по актам, из них СРО {fmt(c['executed']['sro'])}</span></div>"
           f"<div><b>{fmt(c['remaining'])}</b><span>остаток обязательств, из них СРО {fmt(c['remaining_sro'])}</span></div></div>")
    lines = c.get("lines") or []
    if not lines:
        return head + kpi + "<p class=muted small>Строк документов по договору нет.</p>"
    rows = []
    for li in lines:
        s = li["sro"]
        t = tag("yes", "СРО") if s is True else (tag("no", "не СРО") if s is False else tag("q", "решает человек"))
        doc = docs_by_id.get(li["document_id"], {})
        ref = f"{DOC_KIND.get(doc.get('kind', li['doc_kind']), li['doc_kind'])} № {esc(li['doc_number'])}"
        rows.append(f"<tr><td class=small>{ref}</td><td>{esc(li['name'])}</td><td class=num>{fmt(li['amount'])}</td><td>{t}</td>"
                    f"<td class=small>{esc(li.get('code') or '')}</td><td class=small>{esc(li.get('reason') or '')}</td></tr>")
    table = ("<div class=wrap><table><thead><tr><th>Документ</th><th>Строка</th><th class=num>Сумма</th><th>Итог</th><th>Перечень 624</th><th>Основание</th></tr></thead>"
             f"<tbody>{''.join(rows)}</tbody></table></div>")
    return head + kpi + table


def render(res: dict, reg: dict | None) -> str:
    s = res["subject"]
    docs_by_id = {d["id"]: d for d in (reg or {}).get("documents", [])}
    sro_rows = "".join(f"<li>{KIND_LABEL.get(x['kind'], x['kind'])}: {esc(x['name'])}"
                       + (f", рег. № {esc(x['reg_number'])}" if x.get("reg_number") else "")
                       + (f", уровень ОДО {x['odo_level']}" if x.get("odo_level") else ", уровень ОДО не указан")
                       + (f" <span class=muted>({esc(x['source'])})</span>" if x.get("source") else "") + "</li>"
                       for x in s.get("sro", []))
    parts = [f"<title>Обязательства: {esc(s['name'])}</title><style>{CSS}</style><main>",
             f"<h1>Обязательства члена СРО по договорам подряда</h1>",
             f"<p><b>{esc(s['name'])}</b>" + (f", ИНН {esc(s['inn'])}" if s.get("inn") else "") +
             f" · на {esc(res['as_of'])} · базис: {'с НДС' if res['settings']['vat_basis'] == 'with_vat' else 'без НДС'}"
             f" · сформировано {dt.date.today().isoformat()}</p>",
             f"<ul class=small>{sro_rows}</ul>" if sro_rows else "",
             "<div class=disclaimer><b>Информационный расчёт.</b> Суммы разнесены по Перечню видов работ (приказ Минрегиона № 624) "
             "и правилам ГрК РФ о членстве в СРО; числа сняты с копий документов и подлежат сверке с оригиналами. "
             "Строки с пометкой «решает человек» в суммы «СРО» не входят и показаны отдельно. Отчёт не является выводом о нарушении: "
             "соответствие уровню ответственности определяется по данным реестра СРО.</div>"]
    parts.append("<h2>1. Итог: все подходящие договоры</h2><p class=small muted>Договоры подряда с застройщиком, техническим заказчиком, лицом, ответственным за эксплуатацию, региональным оператором, где компания — подрядчик.</p>")
    parts.append(totals_table(res["totals"]["all_qualifying"]))
    parts.append("<h2>2. Итог: только договоры, заключённые конкурентным способом</h2><p class=small muted>Буква ч. 3 ст. 55.8 ГрК РФ. Какая из двух выборок применяется вашей СРО — по её положению о контроле.</p>")
    parts.append(totals_table(res["totals"]["competitive_only"]))
    if res.get("levels_hint"):
        parts.append("<h2>3. Справочно: уровень ответственности по ст. 55.16 ГрК РФ</h2><div class=wrap><table><thead><tr><th>Вид СРО</th><th class=num>Остаток СРО</th><th>Покрывает уровень</th><th>Остаток без разделения → уровень</th><th>Цена СРО → уровень</th><th>Заявленный уровень</th></tr></thead><tbody>")
        for k, h in res["levels_hint"].items():
            parts.append(f"<tr><td>{KIND_LABEL[k]}</td><td class=num>{fmt(h['remaining_sro'])}</td><td>{h['level_covering_remaining_sro']}</td>"
                         f"<td>{h['level_covering_remaining_total']}</td><td>{h['level_covering_price_sro']}</td><td>{h['declared_level'] or '—'}</td></tr>")
        parts.append("</tbody></table></div><p class=small muted>Уровень — минимальный по таблице закона для указанной суммы. Сопоставление с фактическим уровнем члена — по выписке из реестра СРО.</p>")
    parts.append("<h2>4. Договоры</h2><div class=wrap><table><thead><tr><th>Договор</th><th>Контрагент</th><th>Вид</th><th>Способ</th><th>В расчёт</th><th class=num>Цена</th><th class=num>Выполнено</th><th class=num>Остаток</th><th class=num>Остаток СРО</th></tr></thead><tbody>")
    for c in res["contracts"]:
        parts.append(f"<tr><td>{esc(c['number'])}<br><span class=small muted>{esc(c['date'] or '')}</span></td><td>{esc(c['counterparty']['name'])}<br><span class=small muted>{CP_KIND.get(c['counterparty']['kind'], '')}</span></td>"
                     f"<td>{CTR_KIND.get(c['kind'], c['kind'])}</td><td>{PROC.get(c['procurement'], '')}</td><td>{tag('yes' if c['counts_for_odo'] else 'no', 'да' if c['counts_for_odo'] else 'нет')}</td>"
                     f"<td class=num>{fmt(c['price'])}</td><td class=num>{fmt(c['executed']['total'])}</td><td class=num>{fmt(c['remaining'])}</td><td class=num>{fmt(c['remaining_sro'])}</td></tr>")
    parts.append("</tbody></table></div>")
    parts.append("<h2>5. Разбор по договорам: что относится к СРО, что нет</h2>")
    for c in res["contracts"]:
        parts.append(contract_block(c, docs_by_id))
    if res.get("review_queue"):
        parts.append(f"<h2>6. На проверку человеку ({len(res['review_queue'])})</h2><ul>")
        for r in res["review_queue"]:
            parts.append(f"<li>{esc(r['message'])}" + (f" — {fmt(r['amount'])}" if r.get("amount") else "") + "</li>")
        parts.append("</ul>")
    if res.get("warnings"):
        parts.append("<h2>Предупреждения</h2><ul>" + "".join(f"<li>{esc(w)}</li>" for w in res["warnings"]) + "</ul>")
    if reg:
        parts.append("<h2>Источники</h2><div class=wrap><table><thead><tr><th>Документ</th><th>Дата</th><th>Договор</th><th class=num>Без НДС</th><th class=num>С НДС</th><th>Файл</th><th>Уверенность</th></tr></thead><tbody>")
        for d in reg.get("documents", []):
            parts.append(f"<tr><td>{DOC_KIND.get(d['kind'], d['kind'])} № {esc(d['number'])}</td><td>{esc(d.get('date') or '')}</td><td>{esc(d.get('contract_id') or '')}</td>"
                         f"<td class=num>{fmt(d.get('amount_without_vat_rub'))}</td><td class=num>{fmt(d.get('amount_with_vat_rub'))}</td><td class=small>{esc(d['file'])}</td><td>{esc(d.get('extraction_confidence'))}</td></tr>")
        parts.append("</tbody></table></div>")
    parts.append("<h2>Методика</h2><ul>" + "".join(f"<li>{esc(n)}</li>" for n in res["method_notes"]) + "</ul></main>")
    return "\n".join(p for p in parts if p)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("result")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--register")
    args = ap.parse_args(argv)
    with open(args.result, encoding="utf-8") as f:
        res = json.load(f)
    reg = None
    if args.register:
        with open(args.register, encoding="utf-8") as f:
            reg = json.load(f)
    page = render(res, reg)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("<!doctype html><html lang=ru><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'></head><body>")
        f.write(page)
        f.write("</body></html>\n")
    print(f"записано: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
