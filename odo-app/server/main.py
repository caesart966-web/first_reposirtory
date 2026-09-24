"""Веб-оболочка: FastAPI + Jinja2, без сборки фронтенда. Запуск: python -m server"""
from __future__ import annotations

import base64
import datetime as dt
import io
import json
import re
import secrets
import shutil
import threading
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db, engine, export, letters, llm
from .config import APP_PASSWORD, DATA_DIR, ENGINE_DIR, LLM_MODEL, UPLOAD_DIR
from .extract import extract_text, guess_kind
from .parse_contract import build_card

HERE = Path(__file__).resolve().parent
app = FastAPI(title="ОДО-проверка", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
templates = Jinja2Templates(directory=str(HERE / "templates"))
db.init()

RU = {
    "membership": {"yes": "требуется", "no": "не требуется", "conditional": "при условиях", "needs_facts": "нужны факты"},
    "odo": {"yes": "да", "no": "нет", "conditional": "условно", "needs_facts": "нужны факты"},
    "procurement": {"competitive": "конкурентный", "direct": "прямой", "unknown": "не установлен"},
    "status": {"draft": "черновик", "assessed": "рассчитан", "confirmed": "подтверждён", "disputed": "решено иначе"},
    "kind": {"construction": "строительный подряд", "demolition": "снос", "design": "проектирование", "survey": "изыскания", "mixed": "смешанный",
             "supply": "поставка", "services": "услуги", "rent": "аренда", "other": "иное", "unknown": "не установлен"},
    "customer_kind": {"developer": "застройщик", "technical_customer": "технический заказчик", "operator": "лицо, ответственное за эксплуатацию",
                      "regional_operator": "региональный оператор", "general_contractor": "генподрядчик (субподряд)", "contractor": "подрядчик",
                      "individual": "физическое лицо", "state_entity": "орган власти", "other": "иное", "unknown": "не установлен"},
    "work_type": {"construction": "строительство", "reconstruction": "реконструкция", "capital_repair": "капитальный ремонт", "demolition": "снос",
                  "current_repair": "текущий ремонт", "improvement": "благоустройство", "design": "проектирование", "survey": "изыскания", "mixed": "смешанный", "unknown": "не установлен"},
    "procurement_law": {"44-fz": "44-ФЗ", "223-fz": "223-ФЗ", "mandatory_tender": "иные обязательные торги", "voluntary_tender": "добровольный тендер", "unknown": "не установлено"},
    "contract_status": {"active": "действует", "completed": "исполнен", "terminated": "расторгнут", "unknown": "не установлен"},
    "category": {"ordinary": "обычный", "hazardous_48_1": "особо опасный / уникальный (ст. 48.1)", "unknown": "не установлена"},
    "housing": {"none": "нет", "izhs": "ИЖС", "blocked": "блокированная застройка", "mkd_low": "МКД до 3 этажей", "garden": "садовый дом", "auxiliary": "вспомогательная постройка", "unknown": "не установлено"},
    "claim_status": {"founded": "обоснован", "partially": "частично обоснован", "unfounded": "не обоснован", "needs_facts": "нужны факты", "needs_human": "решает человек"},
}
templates.env.globals.update(RU=RU, money=engine.money, llm_on=llm.available(), llm_model=LLM_MODEL)
templates.env.filters["money"] = lambda x: engine.money(x) if x is not None else "—"
templates.env.filters["dmy"] = lambda s: (f"{s[8:10]}.{s[5:7]}.{s[0:4]}" if s and len(s) >= 10 else (s or "—"))


# ---------------------------------------------------------------- auth / user
@app.middleware("http")
async def auth(request: Request, call_next):
    if APP_PASSWORD and not request.url.path.startswith("/static") and request.url.path != "/health":
        hdr = request.headers.get("authorization", "")
        ok = False
        if hdr.startswith("Basic "):
            try:
                _, pwd = base64.b64decode(hdr[6:]).decode("utf-8").split(":", 1)
                ok = secrets.compare_digest(pwd, APP_PASSWORD)
            except Exception:
                ok = False
        if not ok:
            return Response("Нужен пароль", status_code=401, headers={"WWW-Authenticate": 'Basic realm="odo"'})
    return await call_next(request)


def user_of(request: Request) -> str:
    return request.cookies.get("odo_user", "") or "проверяющий"


def render(request: Request, name: str, **ctx):
    ctx.update(request=request, user=user_of(request), llm_on=llm.available())
    return templates.TemplateResponse(request, name, ctx)


@app.post("/whoami")
async def whoami(request: Request, name: str = Form(""), back: str = Form("/")):
    resp = RedirectResponse(back, status_code=303)
    resp.set_cookie("odo_user", name.strip()[:80], max_age=365 * 24 * 3600)
    return resp


@app.get("/health")
async def health():
    return {"ok": True}


# ---------------------------------------------------------------- расчёты по реестру
def effective_price(card: dict) -> float | None:
    c = card["contract"]
    p = c.get("price_rub")
    for a in c.get("addenda") or []:
        if a.get("price_rub") is not None:
            p = a["price_rub"]
    return p


def contract_row(ct: dict) -> dict:
    card, a = ct.get("card") or {}, ct.get("assessment")
    v = (a or {}).get("verdict") or {}
    c = card.get("contract", {})
    price = effective_price(card) if card else None
    remaining = v.get("remaining_rub") if v else (None if price is None else price - (c.get("executed_rub") or 0))
    odo = v.get("counts_for_odo")
    deadline, overdue = None, False
    if c.get("date"):
        deadline = working_days_after(c["date"], 3)
        overdue = (not ct.get("sro_notified")) and dt.date.today().isoformat() > deadline
    return {
        "id": ct["id"], "number": c.get("number") or ct.get("number") or "—", "date": c.get("date"), "customer": card.get("customer", {}).get("name", "—"),
        "customer_inn": card.get("customer", {}).get("inn"), "price": price, "executed": c.get("executed_rub"), "remaining": remaining,
        "procurement": c.get("procurement"), "procurement_ru": RU["procurement"].get(c.get("procurement"), "—"),
        "membership": v.get("membership_required"), "membership_ru": RU["membership"].get(v.get("membership_required"), "—"),
        "odo": odo, "odo_ru": RU["odo"].get(odo, "—"), "odo_amount": (remaining or 0) if odo == "yes" else 0.0,
        "status": ct["status"], "decision_ru": RU["status"].get(ct["status"], ct["status"]), "decided_by": ct.get("decided_by") or "",
        "notified": bool(ct.get("sro_notified")), "notified_ru": ("да, " + (ct.get("sro_notified_date") or "")) if ct.get("sro_notified") else "нет",
        "notify_deadline": deadline, "notify_overdue": overdue, "confidence": v.get("confidence"), "summary": v.get("summary"),
        "needs": (a or {}).get("missing_facts") or [], "work_type": card.get("work_type"),
    }


def working_days_after(date_iso: str, n: int) -> str:
    d = dt.date.fromisoformat(date_iso)
    k = 0
    while k < n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            k += 1
    return d.isoformat()


def company_view(cid: int):
    comp = db.company(cid)
    if not comp:
        return None, [], {}, []
    rows = [contract_row(ct) for ct in db.contracts_of(cid)]
    odo_rows = [r for r in rows if r["odo"] == "yes"]
    totals = {"odo_sum": round(sum(r["odo_amount"] for r in odo_rows), 2), "n_all": len(rows), "n_odo": len(odo_rows),
              "n_open": sum(1 for r in rows if r["odo"] in ("needs_facts", "conditional") or r["status"] == "draft"),
              "n_no": sum(1 for r in rows if r["odo"] == "no")}
    lv = engine.levels()["odo"]["build"]["levels"]
    if comp.get("odo_level"):
        L = next((x for x in lv if x["level"] == comp["odo_level"]), None)
        if L:
            totals["level"] = L
            totals["level_share"] = (totals["odo_sum"] / L["limit_rub"] * 100) if L.get("limit_rub") else None
    warnings = splitting_warnings(rows) + [f"Договор {r['number']}: уведомление в СРО просрочено (срок {r['notify_deadline']})." for r in rows if r["notify_overdue"]]
    return comp, rows, totals, warnings


def splitting_warnings(rows: list[dict]) -> list[str]:
    thr = engine.levels()["thresholds"]["build_contract_rub"]["value"]
    by = {}
    for r in rows:
        if r["price"] is not None and r["price"] <= thr and r["date"]:
            by.setdefault(r["customer_inn"] or r["customer"], []).append(r)
    out = []
    for key, lst in by.items():
        if len(lst) >= 2:
            ds = sorted(dt.date.fromisoformat(r["date"]) for r in lst)
            if (ds[-1] - ds[0]).days <= 90:
                out.append(f"У заказчика «{lst[0]['customer']}» {len(lst)} договора ниже порога за {(ds[-1] - ds[0]).days} дн. ({', '.join(r['number'] for r in lst)}): проверьте, не дробление ли это одного объёма работ.")
    return out


# ---------------------------------------------------------------- страницы
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    comps = []
    for c in db.companies():
        _, rows, totals, warnings = company_view(c["id"])
        comps.append({**c, "totals": totals, "n_warn": len(warnings)})
    return render(request, "index.html", companies=comps)


@app.post("/companies")
async def companies_add(request: Request, name: str = Form(...), inn: str = Form(""), sro_name: str = Form(""), odo_level: str = Form("")):
    cid = db.add_company(name.strip(), inn.strip() or None, None, sro_name.strip() or None, int(odo_level) if odo_level.strip().isdigit() else None)
    db.log(user_of(request), "company.add", None, name)
    return RedirectResponse(f"/company/{cid}", status_code=303)


@app.get("/company/{cid}", response_class=HTMLResponse)
async def company_page(request: Request, cid: int):
    comp, rows, totals, warnings = company_view(cid)
    if not comp:
        return RedirectResponse("/", status_code=303)
    return render(request, "company.html", company=comp, rows=rows, totals=totals, warnings=warnings, levels=engine.levels()["odo"]["build"]["levels"])


@app.post("/company/{cid}/settings")
async def company_settings(request: Request, cid: int, name: str = Form(...), inn: str = Form(""), kpp: str = Form(""), sro_name: str = Form(""),
                           odo_level: str = Form(""), vv_level: str = Form(""), notes: str = Form("")):
    db.update_company(cid, name=name.strip(), inn=inn.strip() or None, kpp=kpp.strip() or None, sro_name=sro_name.strip() or None,
                      odo_level=int(odo_level) if odo_level.strip().isdigit() else None, vv_level=int(vv_level) if vv_level.strip().isdigit() else None, notes=notes.strip() or None)
    return RedirectResponse(f"/company/{cid}", status_code=303)


@app.post("/company/{cid}/delete")
async def company_delete(request: Request, cid: int, confirm: str = Form("")):
    if confirm == "да":
        for ct in db.contracts_of(cid):
            _remove_files(ct["id"])
        db.delete_company(cid)
        db.log(user_of(request), "company.delete", None, str(cid))
    return RedirectResponse("/", status_code=303)


@app.get("/company/{cid}/export.xlsx")
async def company_xlsx(cid: int):
    comp, rows, totals, _ = company_view(cid)
    path = DATA_DIR / f"reestr-{cid}.xlsx"
    export.register_xlsx(comp, rows, totals, path)
    return FileResponse(path, filename=f"Реестр {comp['name']}.xlsx".replace("/", "-"), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/company/{cid}/report", response_class=HTMLResponse)
async def company_report(request: Request, cid: int):
    comp, rows, totals, warnings = company_view(cid)
    policy = engine.policy()
    return render(request, "report.html", company=comp, rows=rows, totals=totals, warnings=warnings, policy=policy, today=dt.date.today().isoformat())


# ---------------------------------------------------------------- новый договор
@app.get("/company/{cid}/contracts/new", response_class=HTMLResponse)
async def contract_new(request: Request, cid: int):
    comp = db.company(cid)
    from .extract import ocr_available
    return render(request, "upload.html", company=comp, ocr_on=ocr_available())


JOBS: dict[int, dict] = {}   # ход разбора по договорам: {ct_id: {stage, file, files_done, files_total, page, pages, started, error}}


@app.post("/company/{cid}/contracts/new")
async def contract_upload(request: Request, cid: int, files: list[UploadFile] = File(...), use_llm: str = Form("")):
    """Файлы сохраняются сразу, разбор (с распознаванием сканов) идёт в фоне — страница прогресса опрашивает состояние."""
    comp = db.company(cid)
    ct_id = db.add_contract(cid, None, {}, {"needs_review": [], "warnings": [], "hints": {}})
    folder = UPLOAD_DIR / str(ct_id)
    folder.mkdir(parents=True, exist_ok=True)
    saved = []
    for up in files:
        if not up.filename:
            continue
        safe = re.sub(r"[^\w.\-() а-яА-ЯёЁ№]", "_", up.filename)[:150]
        dest = folder / safe
        with open(dest, "wb") as f:
            shutil.copyfileobj(up.file, f)
        saved.append((up.filename, dest))
    JOBS[ct_id] = {"stage": "queued", "file": "", "files_done": 0, "files_total": len(saved), "page": 0, "pages": 0, "started": time.time(), "error": None}
    threading.Thread(target=_process_upload, args=(ct_id, cid, comp, saved, bool(use_llm and llm.available()), user_of(request)), daemon=True).start()
    return RedirectResponse(f"/contract/{ct_id}/progress", status_code=303)


def _process_upload(ct_id: int, cid: int, comp: dict, saved: list, use_llm: bool, user: str):
    job = JOBS[ct_id]
    try:
        docs = []
        for i, (filename, dest) in enumerate(saved):
            job.update(stage="extract", file=filename, files_done=i, page=0, pages=0)

            def progress(page, pages, stage, _job=job):
                _job.update(page=page, pages=pages, stage=("ocr" if stage == "ocr" else "extract"))

            text, meta = extract_text(dest, progress=progress)
            db.add_file(ct_id, filename, str(dest.relative_to(DATA_DIR)), meta["kind_hint"], len(text), meta["scanned"])
            docs.append({"filename": filename, "kind": meta["kind_hint"], "text": text, "scanned": meta["scanned"], "ocr": meta.get("ocr", False)})
        job.update(stage="parse", files_done=len(saved), file="")
        member = {"name": comp["name"], "inn": comp.get("inn"), "sro_kinds": ["build"]}
        card, meta = build_card(member, docs)
        if use_llm:
            job.update(stage="llm")
            card, meta = llm.merge(card, llm.extract_card(docs, engine.card_schema(), member), meta)
        scanned = [d["filename"] for d in docs if d.get("scanned")]
        if scanned:
            meta["warnings"].append("Скан без текстового слоя, распознавание недоступно или не дало текста: " + ", ".join(scanned) + ". Данные из этого файла надо внести вручную.")
        ocred = [d["filename"] for d in docs if d.get("ocr")]
        if ocred:
            meta["warnings"].append("Распознано со скана: " + ", ".join(ocred) + ". Проверьте цифры — распознавание может ошибаться в отдельных знаках.")
        dup = db.find_contract_by_number(cid, card["contract"].get("number"))
        if dup and dup["id"] != ct_id:
            meta["warnings"].append(f"Договор с номером {card['contract']['number']} уже есть в реестре (№ записи {dup['id']}).")
        db.update_contract(ct_id, number=card["contract"].get("number") or None, card=card, draft_meta=meta)
        db.log(user, "contract.upload", ct_id, ", ".join(d["filename"] for d in docs))
        job.update(stage="done")
    except Exception as e:  # noqa: BLE001 — ошибку показываем на странице прогресса, а не теряем в фоне
        import traceback
        job.update(stage="error", error=f"{e}\n{traceback.format_exc()[-1500:]}")


@app.get("/contract/{ct_id}/progress", response_class=HTMLResponse)
async def progress_page(request: Request, ct_id: int):
    ct = db.contract(ct_id)
    if not ct:
        return RedirectResponse("/", status_code=303)
    job = JOBS.get(ct_id)
    if not job or job["stage"] == "done":
        return RedirectResponse(f"/contract/{ct_id}/card", status_code=303)
    return render(request, "progress.html", ct=ct, company=db.company(ct["company_id"]), job=job)


@app.get("/contract/{ct_id}/progress.json")
async def progress_json(ct_id: int):
    job = JOBS.get(ct_id)
    if not job:
        return JSONResponse({"stage": "done"})
    out = dict(job)
    out["elapsed"] = round(time.time() - job["started"])
    # оценка остатка: по средней скорости страниц текущего файла
    if job["stage"] == "ocr" and job["page"] > 0 and job["pages"]:
        per_page = out["elapsed"] / max(job["page"], 1)
        out["eta"] = round(per_page * (job["pages"] - job["page"]))
    else:
        out["eta"] = None
    return JSONResponse(out)


def file_path(f: dict) -> Path:
    """Путь к загруженному файлу. В базе он хранится относительно папки данных, чтобы папку можно было
    переносить между компьютерами; старые абсолютные пути и файлы, переехавшие вместе с папкой, тоже находятся."""
    p = Path(f["stored_path"])
    if not p.is_absolute():
        p = DATA_DIR / p
    if not p.exists():
        alt = UPLOAD_DIR / str(f["contract_id"]) / Path(f["stored_path"]).name
        if alt.exists():
            p = alt
    return p


def _remove_files(ct_id: int):
    folder = UPLOAD_DIR / str(ct_id)
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)


# ---------------------------------------------------------------- карточка
@app.get("/contract/{ct_id}/card", response_class=HTMLResponse)
async def card_page(request: Request, ct_id: int, errors: str = ""):
    ct = db.contract(ct_id)
    if not ct:
        return RedirectResponse("/", status_code=303)
    job = JOBS.get(ct_id)
    if job and job["stage"] not in ("done", "error"):
        return RedirectResponse(f"/contract/{ct_id}/progress", status_code=303)
    comp = db.company(ct["company_id"])
    return render(request, "card.html", ct=ct, card=ct["card"], meta=ct["draft_meta"] or {}, company=comp, files=db.files_of(ct_id),
                  errors=[e for e in errors.split("||") if e])


def _f(form, key, default=None):
    v = form.get(key)
    if v is None:
        return default
    v = str(v).strip()
    return v if v != "" else default


def _num(form, key):
    v = _f(form, key)
    if v is None:
        return None
    v = v.replace(" ", "").replace(" ", "").replace(",", ".").replace("₽", "")
    try:
        return round(float(v), 2)
    except ValueError:
        return None


def _bool(form, key):
    v = _f(form, key)
    return None if v in (None, "null") else v == "true"


@app.post("/contract/{ct_id}/card")
async def card_save(request: Request, ct_id: int):
    form = await request.form()
    ct = db.contract(ct_id)
    old = ct["card"] or {}
    card = json.loads(json.dumps(old)) if old else {"schema_version": "1"}
    card["schema_version"] = "1"
    card["member"] = {"name": _f(form, "member_name", ""), "inn": _f(form, "member_inn"), "role": _f(form, "member_role", "contractor"),
                      "is_state_entity": _bool(form, "member_is_state_entity"), "sro_kinds": form.getlist("member_sro_kinds") or ["build"], "membership_date": _f(form, "membership_date")}
    addenda = []
    for i in range(int(_f(form, "addenda_n", "0") or 0)):
        n = _f(form, f"add_number_{i}")
        if n:
            addenda.append({"number": n, "date": _f(form, f"add_date_{i}"), "price_rub": _num(form, f"add_price_{i}"), "note": _f(form, f"add_note_{i}")})
    card["contract"] = {
        "number": _f(form, "number", ""), "date": _f(form, "date"), "subject_text": _f(form, "subject_text", ""),
        "kind": _f(form, "kind", "unknown"), "kind_basis": _f(form, "kind_basis"), "mixed_parts": old.get("contract", {}).get("mixed_parts", []),
        "price_rub": _num(form, "price_rub"), "price_basis": _f(form, "price_basis"), "price_includes_vat": _bool(form, "price_includes_vat"),
        "addenda": addenda, "status": _f(form, "status", "unknown"), "status_basis": _f(form, "status_basis"),
        "period_from": _f(form, "period_from"), "period_to": _f(form, "period_to"),
        "procurement": _f(form, "procurement", "unknown"), "procurement_basis": _f(form, "procurement_basis"),
        "nmck_rub": _num(form, "nmck_rub"), "nmck_basis": _f(form, "nmck_basis"),
        "procurement_law": _f(form, "procurement_law") if _f(form, "procurement_law") not in (None, "null") else None,
        "executed_rub": _num(form, "executed_rub"), "executed_basis": _f(form, "executed_basis"),
        "has_final_act": _bool(form, "has_final_act"), "termination_document": _f(form, "termination_document"),
    }
    card["customer"] = {"name": _f(form, "customer_name", ""), "inn": _f(form, "customer_inn"), "kind": _f(form, "customer_kind", "unknown"), "kind_basis": _f(form, "customer_kind_basis")}
    card["object"] = {"name": _f(form, "object_name", ""), "address": _f(form, "object_address"), "cadastral": _f(form, "cadastral"),
                      "is_capital": _bool(form, "is_capital"), "permit_required": _bool(form, "permit_required"), "housing_type": _f(form, "housing_type", "unknown"),
                      "category": _f(form, "category", "unknown"), "basis": _f(form, "object_basis")}
    card["work_type"] = _f(form, "work_type", "unknown")
    works = []
    for i in range(int(_f(form, "works_n", "0") or 0)):
        n = _f(form, f"work_name_{i}")
        if n:
            hd = _f(form, f"work_human_{i}")
            works.append({"name": n, "amount_rub": _num(form, f"work_amount_{i}"), "source": _f(form, f"work_source_{i}"),
                          "human_decision": ({"sro": hd == "sro", "perechen_code": None, "note": "решение проверяющего"} if hd in ("sro", "nosro") else None)})
    card["works"] = works
    card["sources"] = old.get("sources") or [{"file": f["filename"], "kind": f["kind"], "pages": None, "extraction_confidence": None} for f in db.files_of(ct_id)]
    card["as_of"] = _f(form, "as_of") or dt.date.today().isoformat()
    card["notes"] = _f(form, "notes")
    errs = engine.validate_card(card)
    if not card["contract"]["number"]:
        errs.append("номер договора обязателен")
    if errs:
        db.update_contract(ct_id, card=card)
        return RedirectResponse(f"/contract/{ct_id}/card?errors=" + "||".join(errs)[:1500], status_code=303)
    a, md = engine.assess_card(card)
    db.update_contract(ct_id, number=card["contract"]["number"], card=card, assessment=a, status="assessed", decision=None, decision_note=None, decided_by=None, decided_at=None, case_id=None)
    db.log(user_of(request), "contract.assess", ct_id, f"{a['verdict']['membership_required']}/{a['verdict']['counts_for_odo']}")
    return RedirectResponse(f"/contract/{ct_id}", status_code=303)


# ---------------------------------------------------------------- заключение
@app.get("/contract/{ct_id}", response_class=HTMLResponse)
async def contract_page(request: Request, ct_id: int):
    ct = db.contract(ct_id)
    if not ct:
        return RedirectResponse("/", status_code=303)
    if not ct.get("assessment"):
        return RedirectResponse(f"/contract/{ct_id}/card", status_code=303)
    comp = db.company(ct["company_id"])
    row = contract_row(ct)
    return render(request, "contract.html", ct=ct, card=ct["card"], a=ct["assessment"], company=comp, row=row, files=db.files_of(ct_id),
                  letters=db.letters_of(ct_id), reasons=short_reasons(ct["assessment"]), eis_url=eis_link(ct["card"]))


def eis_link(card: dict) -> str | None:
    c = card.get("contract", {})
    m = re.match(r"(\d{19})", c.get("number") or "")
    if m:
        return f"https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber={m.group(1)}"
    return None


def short_reasons(a: dict) -> list[str]:
    out = []
    for f in a.get("findings", []):
        if f["step"] in (3, 4, 5) and f.get("conclusion") in ("yes", "no", "conditional", "needs_facts"):
            first = re.split(r"(?<=[.!?])\s", f["explanation"].strip(), maxsplit=1)[0]
            out.append(f"{f['title']}: {first}")
    return out[:3]


@app.post("/contract/{ct_id}/decision")
async def contract_decision(request: Request, ct_id: int, verdict: str = Form(...), note: str = Form(""), by: str = Form("")):
    ct = db.contract(ct_id)
    a = ct["assessment"]
    v = a["verdict"]
    by = by.strip() or user_of(request)
    if verdict == "agree":
        decision = ("Входит в ОДО" if v["counts_for_odo"] == "yes" else "Не входит в ОДО" if v["counts_for_odo"] == "no" else "Требует уточнения") + ": " + (v.get("summary") or "")
        status = "confirmed"
    else:
        decision = note.strip() or "Решено иначе, чем предложил расчёт"
        status = "disputed"
    case_id = engine.add_precedent_from_assessment(a, decision, note.strip() or None, by)
    db.update_contract(ct_id, status=status, decision=decision, decision_note=note.strip() or None, decided_by=by, decided_at=db.now(), case_id=case_id)
    db.log(by, f"contract.{status}", ct_id, case_id)
    return RedirectResponse(f"/contract/{ct_id}", status_code=303)


@app.post("/contract/{ct_id}/notify")
async def contract_notify(request: Request, ct_id: int, notified: str = Form(""), date: str = Form("")):
    db.update_contract(ct_id, sro_notified=1 if notified == "yes" else 0, sro_notified_date=date.strip() or None)
    return RedirectResponse(f"/contract/{ct_id}", status_code=303)


@app.post("/contract/{ct_id}/delete")
async def contract_delete(request: Request, ct_id: int, confirm: str = Form("")):
    ct = db.contract(ct_id)
    cid = ct["company_id"] if ct else None
    if ct and confirm == "да":
        _remove_files(ct_id)
        db.delete_contract(ct_id)
        db.log(user_of(request), "contract.delete", ct_id, ct.get("number"))
    return RedirectResponse(f"/company/{cid}" if cid else "/", status_code=303)


@app.get("/contract/{ct_id}/zaklyuchenie.{fmt}")
async def contract_download(ct_id: int, fmt: str):
    ct = db.contract(ct_id)
    _, md = engine.assess_card(ct["card"])
    name = f"Заключение по договору {ct['number'] or ct_id}".replace("/", "-")
    if fmt == "docx":
        path = DATA_DIR / f"z-{ct_id}.docx"
        export.md_to_docx(md, path)
        return FileResponse(path, filename=name + ".docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    if fmt == "json":
        return JSONResponse(ct["assessment"])
    return Response(md, media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(name + ".md")})


@app.get("/contract/{ct_id}/files/{fid}")
async def contract_file(ct_id: int, fid: int):
    f = db.file(fid)
    if not f or f["contract_id"] != ct_id:
        return Response(status_code=404)
    p = file_path(f)
    if not p.exists():
        return Response("Файл не найден в папке данных", status_code=404)
    return FileResponse(str(p), filename=f["filename"])


# ---------------------------------------------------------------- письма-возражения
@app.get("/contract/{ct_id}/letter", response_class=HTMLResponse)
async def letter_page(request: Request, ct_id: int):
    ct = db.contract(ct_id)
    return render(request, "letter.html", ct=ct, company=db.company(ct["company_id"]), catalogue=engine.objection_catalogue(), claims=None, text="", meta=None)


@app.post("/contract/{ct_id}/letter/detect", response_class=HTMLResponse)
async def letter_detect(request: Request, ct_id: int, text: str = Form(""), file: UploadFile | None = File(None)):
    ct = db.contract(ct_id)
    if file and file.filename:
        folder = UPLOAD_DIR / str(ct_id) / "letters"
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / re.sub(r"[^\w.\-() а-яА-ЯёЁ№]", "_", file.filename)[:150]
        with open(dest, "wb") as fh:
            shutil.copyfileobj(file.file, fh)
        t, _ = extract_text(dest)
        text = (text + "\n\n" + t).strip()
    claims = letters.detect_claims(text)
    return render(request, "letter.html", ct=ct, company=db.company(ct["company_id"]), catalogue=engine.objection_catalogue(), claims=claims, text=text, meta=letters.letter_meta(text))


@app.post("/contract/{ct_id}/letter/analyze")
async def letter_analyze(request: Request, ct_id: int):
    form = await request.form()
    ct = db.contract(ct_id)
    text = _f(form, "text", "")
    claims = []
    for i in range(int(_f(form, "claims_n", "0") or 0)):
        if _f(form, f"claim_drop_{i}"):
            continue
        q = _f(form, f"claim_quote_{i}")
        if q:
            claims.append({"type": _f(form, f"claim_type_{i}", "other"), "quote": q, "facts": {}})
    obj = {"schema_version": "1", "letter": {"from": _f(form, "letter_from", "") or "", "to": None, "date": _f(form, "letter_date"), "number": _f(form, "letter_number"),
                                              "summary": _f(form, "letter_summary", "") or (text[:200] if text else ""), "file": None, "contract_number": ct["card"]["contract"]["number"]},
           "claims": claims}
    an, md = engine.analyze_letter(obj, ct["card"], ct["assessment"])
    lid = db.add_letter(ct_id, text, obj, an, md)
    db.log(user_of(request), "letter.analyze", ct_id, f"{len(claims)} доводов")
    return RedirectResponse(f"/letter/{lid}", status_code=303)


@app.get("/letter/{lid}", response_class=HTMLResponse)
async def letter_result(request: Request, lid: int):
    L = db.letter(lid)
    if not L:
        return RedirectResponse("/", status_code=303)
    ct = db.contract(L["contract_id"])
    return render(request, "letter_result.html", L=L, ct=ct, company=db.company(ct["company_id"]), catalogue=engine.objection_catalogue())


@app.post("/letter/{lid}/decision")
async def letter_decision(request: Request, lid: int, decision: str = Form(...), note: str = Form(""), by: str = Form("")):
    L = db.letter(lid)
    o = dict(L["objection"])
    o["analysis"] = L["analysis"]
    case_id = engine.add_precedent_from_objection(o, decision.strip(), note.strip() or None, by.strip() or user_of(request))
    db.log(by.strip() or user_of(request), "letter.decision", L["contract_id"], case_id)
    return RedirectResponse(f"/letter/{lid}", status_code=303)


@app.get("/letter/{lid}/otvet.{fmt}")
async def letter_download(lid: int, fmt: str):
    L = db.letter(lid)
    name = f"Ответ на письмо {L['id']}"
    if fmt == "docx":
        path = DATA_DIR / f"otvet-{lid}.docx"
        export.md_to_docx(L["reply_md"], path)
        return FileResponse(path, filename=name + ".docx", media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    return Response(L["reply_md"], media_type="text/markdown; charset=utf-8")


# ---------------------------------------------------------------- справочники
@app.get("/laws", response_class=HTMLResponse)
async def laws_page(request: Request, q: str = ""):
    norms = engine.law()
    items = [(k, v) for k, v in norms.items() if not q or q.lower() in (k + v.get("cite", "") + v.get("gist", "")).lower()]
    return render(request, "laws.html", items=items, q=q, total=len(norms))


@app.get("/cases", response_class=HTMLResponse)
async def cases_page(request: Request):
    return render(request, "cases.html", cases=list(reversed(engine.precedents())), suggestions=engine.rule_suggestions())


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, selftest: str = ""):
    tests = engine.engine_tests() if selftest else None
    return render(request, "settings.html", policy=engine.policy(), engine_dir=str(ENGINE_DIR), data_dir=str(DATA_DIR), tests=tests,
                  password_on=bool(APP_PASSWORD), log=db.log_tail(100))
