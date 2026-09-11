#!/usr/bin/env python3
"""Классификация строк реестра: вид работ по Перечню 624 → СРО / не СРО.

Детерминированные правила (data/rules.json) по наименованию строки плюс два
контекста: вид договора и категория объекта (ст. 48.1 ГрК РФ). Скрипт не
принимает решений за человека: всё, что ниже порога уверенности или зависит
от незаданной категории объекта, получает review_status = pending.

Использование:
    python3 classify.py register.json                # разметить и записать на место
    python3 classify.py register.json -o out.json    # записать в другой файл
    python3 classify.py --text "Устройство кровли из рулонных материалов"
    python3 classify.py --text "..." --object hazardous_48_1

Строки с review_status confirmed/corrected/rejected не трогаются (--force
перезапишет и их).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

DEFAULT_CONFIDENCE = 0.85
NON_PODRYAD_KINDS = {"supply", "services", "other"}
SECTION_KIND = {"I": "survey", "II": "design", "III": "build"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def norm(text: str) -> str:
    t = (text or "").lower().replace("ё", "е")
    t = re.sub(r"\s+", " ", t).strip()
    return t


class Perechen:
    """Индекс Перечня 624: код → {section, sro_kind, title, asterisk}."""

    def __init__(self, data):
        self.data = data
        self.index = {}
        for s in data["sections"]:
            kind = s["sro_kind"]
            for g in s["groups"]:
                gcode = f"{s['id']}/{g['code']}"
                self.index[gcode] = {
                    "section": s["id"], "sro_kind": kind, "title": g["title"],
                    "asterisk": bool(g["asterisk"]), "group": g["code"],
                }
                for it in g["items"]:
                    self.index[f"{s['id']}/{it['code']}"] = {
                        "section": s["id"], "sro_kind": kind, "title": it["title"],
                        "asterisk": bool(it["asterisk"]) or bool(g["asterisk"]),
                        "group": g["code"],
                    }

    def get(self, code):
        return self.index.get(code)


class Classifier:
    def __init__(self, rules=None, perechen=None):
        rules = rules or load_json(os.path.join(DATA, "rules.json"))
        perechen = perechen or load_json(os.path.join(DATA, "perechen-624.json"))
        self.perechen = Perechen(perechen)
        self.rules = []
        for r in rules["rules"]:
            self.rules.append((r, re.compile(r["pattern"])))

    # ---- сопоставление -------------------------------------------------
    def matches(self, text: str):
        t = norm(text)
        out = []
        for r, rx in self.rules:
            if rx.search(t):
                out.append(r)
        out.sort(key=lambda r: -r["priority"])
        return out

    def _outcome(self, res, object_category):
        """Итог правила (True/False/None) без учёта уверенности — для сравнения ничьих."""
        k = res.get("kind")
        if k in ("non_work", "not_in_list"):
            return False
        if k != "perechen":
            return None
        item = self.perechen.get(res.get("code"))
        if item is None:
            return None
        if not item["asterisk"]:
            return True
        return {"hazardous_48_1": True, "ordinary": False}.get(object_category)

    def classify_text(self, text: str, object_category: str = "unknown",
                      contract_kind: str | None = None, threshold: float = 0.7):
        """Классификация одной строки. Возвращает dict по схеме classification."""
        c = {
            "kind": "unclassified", "sro": None, "sro_kind": None,
            "perechen_code": None, "perechen_title": None, "asterisk": None,
            "category": None, "rule_id": None, "reason": "", "confidence": 0.0,
            "note": None, "alternatives": [], "review_status": "pending",
            "human_note": None,
        }
        if contract_kind in NON_PODRYAD_KINDS:
            c.update({
                "kind": "non_work", "sro": False,
                "category": {"supply": "supply", "services": "services"}.get(contract_kind),
                "reason": f"Договор не подрядный (вид: {contract_kind}) — в совокупный размер обязательств не входит",
                "confidence": 0.95, "review_status": "auto",
            })
            return c

        ms = self.matches(text)
        if not ms:
            c["reason"] = "Ни одно правило не сработало — определить вид работ вручную"
            return c

        top = ms[0]
        res = top["result"]
        conf = float(res.get("confidence", DEFAULT_CONFIDENCE))
        alternatives, outcomes = [], set()
        for r in ms[1:]:
            rr = r["result"]
            same = (rr.get("kind") == res.get("kind") and rr.get("code") == res.get("code"))
            if r["priority"] == top["priority"] and not same:
                alternatives.append(f"{r['id']} → {rr.get('code') or rr.get('kind')}")
                outcomes.add(self._outcome(rr, object_category))
        if alternatives and outcomes != {self._outcome(res, object_category)}:
            conf = min(conf, 0.5)
        c["alternatives"] = alternatives
        c["rule_id"] = top["id"]
        c["kind"] = res["kind"]
        c["note"] = res.get("note")

        if res["kind"] == "non_work":
            c.update({"sro": False, "category": res.get("category"), "reason": res["reason"]})
        elif res["kind"] == "not_in_list":
            c.update({"sro": False, "reason": res["reason"]})
        elif res["kind"] == "review":
            c.update({"sro": None, "reason": res["reason"], "perechen_code": res.get("candidate")})
            conf = min(conf, 0.4)
        elif res["kind"] == "perechen":
            item = self.perechen.get(res["code"])
            if item is None:
                c.update({"kind": "unclassified", "reason": f"Код {res['code']} не найден в Перечне"})
                conf = 0.0
            else:
                c.update({
                    "perechen_code": res["code"], "perechen_title": item["title"],
                    "asterisk": item["asterisk"], "sro_kind": item["sro_kind"],
                })
                base = f"Перечень 624, п. {res['code'].split('/', 1)[1]} раздела {item['section']}: {item['title']}"
                if not item["asterisk"]:
                    c.update({"sro": True, "reason": base})
                else:
                    if object_category == "hazardous_48_1":
                        c.update({"sro": True, "reason": base + " — со звёздочкой; объект по ст. 48.1 ГрК РФ, поэтому в расчёт"})
                    elif object_category == "ordinary":
                        c.update({"sro": False, "reason": base + " — со звёздочкой: на обычном объекте (не ст. 48.1) допуска не требовало, в расчёт не идёт"})
                    else:
                        c.update({"sro": None, "reason": base + " — со звёздочкой: категория объекта не задана, решает человек"})
                        conf = min(conf, 0.5)
        c["confidence"] = round(conf, 2)
        c["review_status"] = "auto" if (c["sro"] is not None and conf >= threshold) else "pending"
        if alternatives and c["note"] is None:
            c["note"] = "Несколько правил равного приоритета: " + "; ".join(alternatives)
        return c


# ---- реестр -------------------------------------------------------------

def classify_register(reg: dict, clf: Classifier, force: bool = False) -> dict:
    settings = reg.get("settings") or {}
    threshold = float(settings.get("review_threshold", 0.7))
    default_cat = settings.get("default_object_category", "unknown")
    objects = {o["id"]: o for o in reg.get("objects", [])}
    contracts = {c["id"]: c for c in reg.get("contracts", [])}
    documents = {d["id"]: d for d in reg.get("documents", [])}

    stats = {"total": 0, "auto": 0, "pending": 0, "kept": 0, "summary": 0,
             "sro_true": 0, "sro_false": 0, "sro_null": 0}
    for li in reg.get("line_items", []):
        stats["total"] += 1
        prev = li.get("classification")
        if prev and prev.get("review_status") in ("confirmed", "corrected", "rejected") and not force:
            stats["kept"] += 1
            continue
        if li.get("is_summary"):
            li["classification"] = {
                "kind": "summary", "sro": None, "sro_kind": None, "perechen_code": None,
                "perechen_title": None, "asterisk": None, "category": None, "rule_id": None,
                "reason": "Итоговая строка, не суммируется", "confidence": 1.0, "note": None,
                "alternatives": [], "review_status": "auto", "human_note": None,
            }
            stats["summary"] += 1
            continue
        ctr = contracts.get(li.get("contract_id") or "") or {}
        doc = documents.get(li.get("document_id") or "") or {}
        obj_id = li.get("object_id") or ctr.get("object_id")
        obj = objects.get(obj_id or "") or {}
        cat = obj.get("category") or default_cat
        c = clf.classify_text(li["name"], object_category=cat,
                              contract_kind=ctr.get("kind"), threshold=threshold)
        # Строка из раздела Перечня, не совпадающего с видом договора, — пометка.
        ck = ctr.get("sro_kind") or {"construction": "build", "demolition": "build",
                                      "design": "design", "survey": "survey"}.get(ctr.get("kind"))
        if c.get("sro_kind") and ck and ctr.get("kind") != "mixed" and c["sro_kind"] != ck:
            c["note"] = (c.get("note") or "") + f" | Вид работ раздела «{c['sro_kind']}» в договоре вида «{ck}» — смешанный договор?"
            c["review_status"] = "pending"
        if doc.get("kind") in ("ks3", "invoice") and c["kind"] != "summary":
            c["note"] = (c.get("note") or "") + " | Строка из КС-3/счёта-фактуры: в выполненное не идёт (дубль КС-2)"
        li["classification"] = c
        stats[c["review_status"]] += 1
        key = {True: "sro_true", False: "sro_false", None: "sro_null"}[c["sro"]]
        stats[key] += 1
    reg["_classify_stats"] = stats
    return reg


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("register", nargs="?", help="register.json")
    ap.add_argument("-o", "--out", help="куда записать (по умолчанию — на место)")
    ap.add_argument("--text", help="классифицировать одну строку и выйти")
    ap.add_argument("--object", default="unknown", choices=["ordinary", "hazardous_48_1", "unknown"])
    ap.add_argument("--contract-kind", default=None)
    ap.add_argument("--threshold", type=float, default=0.7)
    ap.add_argument("--force", action="store_true", help="перезаписать и подтверждённые человеком строки")
    args = ap.parse_args(argv)

    clf = Classifier()
    if args.text:
        c = clf.classify_text(args.text, object_category=args.object,
                              contract_kind=args.contract_kind, threshold=args.threshold)
        print(json.dumps(c, ensure_ascii=False, indent=2))
        return 0
    if not args.register:
        ap.error("нужен register.json или --text")
    reg = load_json(args.register)
    reg = classify_register(reg, clf, force=args.force)
    stats = reg.pop("_classify_stats")
    out = args.out or args.register
    with open(out, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"строк: {stats['total']}; авто: {stats['auto']}; на проверку: {stats['pending']}; "
          f"оставлено как есть: {stats['kept']}; итоговых: {stats['summary']}")
    print(f"СРО: {stats['sro_true']}; не СРО: {stats['sro_false']}; не решено: {stats['sro_null']}")
    pend = [li for li in reg["line_items"] if (li.get("classification") or {}).get("review_status") == "pending"]
    for li in pend[:50]:
        c = li["classification"]
        print(f"  ? {li['id']}: «{li['name'][:70]}» → {c.get('perechen_code') or c['kind']} ({c['confidence']}): {c['reason'][:90]}")
    if len(pend) > 50:
        print(f"  … и ещё {len(pend) - 50}")
    print(f"записано: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
