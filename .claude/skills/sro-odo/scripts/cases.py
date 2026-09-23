#!/usr/bin/env python3
"""База прецедентов: решённые договоры, возражения и строки — без персональных данных.

    python3 cases.py add case.json                       # добавить готовую запись
    python3 cases.py add --from-assessment a.json --decision "входит в ОДО" --note "..." [--by "Ф. И. О."]
    python3 cases.py add --from-objection o.json --decision "довод отклонён" --note "..."
    python3 cases.py find card.json [-n 5]               # похожие прецеденты
    python3 cases.py list | stats
    python3 cases.py suggest                             # заготовки правил из расхождений человека и скрипта

Хранение: cases/index.jsonl (одна запись в строке) и cases/<id>.json.
Записи анонимны: имена сторон, ИНН и номера договоров не сохраняются —
только признаки (вид договора, заказчик, ценовая полоса, слова предмета,
виды работ) и решение с основанием.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES_DIR = os.path.normpath(os.path.join(HERE, "..", "cases"))
INDEX = os.path.join(CASES_DIR, "index.jsonl")
STOP = {"договор", "договора", "работ", "работы", "работа", "выполнение", "объект", "объекте", "объекта", "полный", "комплекс", "адресу",
        "расположенный", "земельном", "участке", "российская", "федерация", "область", "район", "город", "поселение", "кадастровый", "номер",
        "строительство", "строительства", "многоквартирные", "многоквартирный", "жилые", "жилой", "дома", "дом", "этап", "очередь",
        "услуги", "услуг", "также", "иные", "прочие", "согласно", "приложение", "приложению", "которые", "который", "между"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def tokens(text: str) -> set:
    t = (text or "").lower().replace("ё", "е")
    out = set()
    for w in re.findall(r"[а-яa-z]{4,}", t):
        if w in STOP:
            continue
        out.add(w[:6] if len(w) > 6 else w)
    return out


def price_band(p):
    if p is None:
        return "не установлена"
    for lim, name in [(10e6, "до 10 млн"), (90e6, "10–90 млн"), (500e6, "90–500 млн"), (3e9, "500 млн – 3 млрд"), (10e9, "3–10 млрд")]:
        if p < lim:
            return name
    return "10 млрд и более"


def features_from_card(card: dict, verdict: dict | None = None) -> dict:
    c, cu, ob = card["contract"], card["customer"], card["object"]
    subj = c.get("subject_text", "")
    works = [w["name"] for w in card.get("works", [])]
    kw = tokens(subj) | set().union(*(tokens(w) for w in works)) if works else tokens(subj)
    f = {
        "kind": "contract", "contract_kind": c.get("kind"), "work_type": card.get("work_type"), "customer_kind": cu.get("kind"),
        "member_role": card["member"].get("role"), "procurement": c.get("procurement"), "status": c.get("status"),
        "price_band": price_band(c.get("price_rub")), "object_category": ob.get("category"), "housing_type": ob.get("housing_type"),
        "is_capital": ob.get("is_capital"), "subject_words": sorted(tokens(subj))[:40],
        "works": [{"name": w["name"], "human_sro": (w.get("human_decision") or {}).get("sro")} for w in card.get("works", [])],
        "keywords": sorted(kw),
    }
    if verdict:
        f["auto_verdict"] = {"membership_required": verdict.get("membership_required"), "counts_for_odo": verdict.get("counts_for_odo"),
                             "sro_kind": verdict.get("sro_kind"), "share_sro": verdict.get("share_sro")}
    return f


def load_index() -> list:
    if not os.path.exists(INDEX):
        return []
    out = []
    with open(INDEX, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def next_id(existing: list) -> str:
    year = dt.date.today().year
    nums = [int(c["id"].split("-")[2]) for c in existing if c["id"].startswith(f"case-{year}-")]
    return f"case-{year}-{(max(nums) + 1) if nums else 1:03d}"


def score(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_similar(features: dict, limit: int = 5) -> list:
    idx = load_index()
    fk = set(features.get("keywords") or [])
    out = []
    for c in idx:
        s = score(fk, set(c.get("keywords") or []))
        cf = c.get("features", {})
        for key, w in (("contract_kind", 0.15), ("customer_kind", 0.15), ("work_type", 0.1), ("price_band", 0.05), ("procurement", 0.05)):
            if features.get(key) and cf.get(key) == features.get(key):
                s += w
        if s > 0.3:
            out.append({"id": c["id"], "date": c["date"], "kind": c["kind"], "score": round(min(s, 1.0), 2),
                        "human_decision": c["human"]["decision"], "note": c["human"].get("note"), "basis": c.get("basis", [])})
    out.sort(key=lambda x: -x["score"])
    return out[:limit]


def scrub(text):
    """Убрать из свободного текста номера договоров, ИНН, длинные числа и телефоны."""
    if not isinstance(text, str):
        return text
    text = re.sub(r"№\s*[\w/.-]*\d[\w/.-]*", "№ ***", text)
    text = re.sub(r"\d{6,}", "***", text)
    return text


def scrub_case(case: dict) -> dict:
    h = case.get("human") or {}
    for k in ("decision", "note"):
        if h.get(k):
            h[k] = scrub(h[k])
    a = case.get("auto") or {}
    for k in list(a):
        if isinstance(a[k], str):
            a[k] = scrub(a[k])
    case["features"]["works"] = [{**w, "name": scrub(w.get("name", ""))} for w in case.get("features", {}).get("works", [])]
    return case


def add_case(case: dict) -> str:
    case = scrub_case(case)
    os.makedirs(CASES_DIR, exist_ok=True)
    idx = load_index()
    if not case.get("id"):
        case["id"] = next_id(idx)
    if any(c["id"] == case["id"] for c in idx):
        raise SystemExit(f"прецедент {case['id']} уже есть")
    try:
        import jsonschema
        schema = load_json(os.path.join(HERE, "..", "schemas", "case.schema.json"))
        jsonschema.Draft202012Validator(schema).validate(case)
    except ImportError:
        pass
    with open(os.path.join(CASES_DIR, case["id"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(case, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(INDEX, "a", encoding="utf-8") as f:
        f.write(json.dumps(case, ensure_ascii=False) + "\n")
    return case["id"]


def case_from_assessment(a: dict, decision: str, note: str | None, by: str | None) -> dict:
    r = a["contract_ref"]
    v = a["verdict"]
    subj_words = sorted(set().union(*(tokens(w["name"]) for w in a["works"])) if a["works"] else set())
    feats = {"contract_kind": r["kind"], "work_type": r.get("work_type"), "customer_kind": r["customer_kind"], "member_role": r["role"],
             "procurement": r["procurement"], "status": r["status"], "price_band": r["price_band"], "object_category": r["object_category"],
             "works": [{"name": w["name"], "auto_code": w.get("perechen_code"), "auto_sro": w["sro"]} for w in a["works"]]}
    auto = {"membership_required": v["membership_required"], "counts_for_odo": v["counts_for_odo"], "sro_kind": v["sro_kind"], "share_sro": v["share_sro"]}
    agrees = None
    d = decision.lower()
    if "не входит" in d or "не требует" in d:
        agrees = v["counts_for_odo"] in ("no",) or v["membership_required"] == "no"
    elif "входит" in d or "требует" in d:
        agrees = v["counts_for_odo"] in ("yes", "conditional")
    basis = sorted({b for f in a["findings"] for b in f["basis"]})
    return {"id": None, "date": dt.date.today().isoformat(), "kind": "contract", "features": feats, "auto": auto,
            "human": {"decision": decision, "agrees_with_auto": agrees, "note": note, "decided_by": by},
            "basis": basis, "keywords": subj_words, "rule_suggestion": None, "source_files": []}


def case_from_objection(o: dict, decision: str, note: str | None, by: str | None) -> dict:
    an = o.get("analysis") or {}
    claims = [{"type": c["type"], "auto_status": (c.get("analysis") or {}).get("status")} for c in an.get("claims", [])] or [{"type": c["type"], "auto_status": None} for c in o["claims"]]
    kw = set().union(*(tokens(c["quote"]) for c in o["claims"])) if o["claims"] else set()
    basis = sorted({b for c in an.get("claims", []) for b in (c.get("analysis") or {}).get("basis", [])})
    return {"id": None, "date": dt.date.today().isoformat(), "kind": "objection",
            "features": {"claim_types": [c["type"] for c in o["claims"]], "claims": claims},
            "auto": {"overall": an.get("overall")}, "human": {"decision": decision, "agrees_with_auto": None, "note": note, "decided_by": by},
            "basis": basis, "keywords": sorted(kw), "rule_suggestion": None, "source_files": []}


def suggest(idx: list) -> list:
    """Строки, где человек решил иначе, чем скрипт, — заготовки правил."""
    out = []
    for c in idx:
        for w in c.get("features", {}).get("works", []):
            if w.get("human_sro") is not None and w.get("auto_sro") is not None and w["human_sro"] != w["auto_sro"]:
                kw = sorted(tokens(w["name"]))[:4]
                out.append({"case": c["id"], "line": w["name"], "auto": w["auto_sro"], "human": w["human_sro"],
                            "rule_stub": {"id": f"H-{c['id'][-3:]}-{len(out) + 1}", "priority": 80, "pattern": "|".join(kw),
                                          "result": {"kind": "perechen" if w["human_sro"] else "not_in_list", "code": w.get("human_code"),
                                                     "reason": f"По прецеденту {c['id']}: " + (c["human"].get("note") or "")}}})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("case", nargs="?")
    a.add_argument("--from-assessment")
    a.add_argument("--from-objection")
    a.add_argument("--decision")
    a.add_argument("--note")
    a.add_argument("--by")
    f = sub.add_parser("find")
    f.add_argument("card")
    f.add_argument("-n", type=int, default=5)
    sub.add_parser("list")
    sub.add_parser("stats")
    sub.add_parser("suggest")
    args = ap.parse_args(argv)

    if args.cmd == "add":
        if args.from_assessment:
            if not args.decision:
                ap.error("--decision обязателен")
            case = case_from_assessment(load_json(args.from_assessment), args.decision, args.note, args.by)
        elif args.from_objection:
            if not args.decision:
                ap.error("--decision обязателен")
            case = case_from_objection(load_json(args.from_objection), args.decision, args.note, args.by)
        elif args.case:
            case = load_json(args.case)
        else:
            ap.error("нужен case.json, --from-assessment или --from-objection")
        cid = add_case(case)
        print(f"добавлен {cid} (agrees_with_auto={case['human'].get('agrees_with_auto')})")
        return 0
    if args.cmd == "find":
        data = load_json(args.card)
        feats = features_from_card(data) if "contract" in data and "member" in data else data.get("features", data)
        for p in find_similar(feats, args.n):
            print(f"{p['id']} {p['date']} сходство {p['score']:.2f}: {p['human_decision']}" + (f" — {p['note']}" if p.get("note") else ""))
        return 0
    idx = load_index()
    if args.cmd == "list":
        for c in idx:
            print(f"{c['id']} {c['date']} [{c['kind']}] {c['human']['decision']}" + (f" — {c['human'].get('note')}" if c['human'].get('note') else ""))
    elif args.cmd == "stats":
        n = len(idx)
        agree = sum(1 for c in idx if c["human"].get("agrees_with_auto") is True)
        dis = sum(1 for c in idx if c["human"].get("agrees_with_auto") is False)
        print(f"прецедентов: {n}; скрипт и человек согласны: {agree}; расходятся: {dis}; не оценено: {n - agree - dis}")
        for k in ("contract", "objection", "line_item"):
            print(f"  {k}: {sum(1 for c in idx if c['kind'] == k)}")
    elif args.cmd == "suggest":
        s = suggest(idx)
        if not s:
            print("расхождений по строкам нет — предлагать нечего")
        for x in s:
            print(json.dumps(x, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
