"""Сквозной прогон через HTTP: компания → загрузка → карточка → расчёт → решение → выгрузки → письмо."""
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
TMP = tempfile.mkdtemp(prefix="odo-test-")
os.environ["ODO_DATA_DIR"] = TMP
os.environ["ODO_CASES_DIR"] = os.path.join(TMP, "cases")
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from server.main import app  # noqa: E402

FX = ROOT / "tests" / "fixtures"
client = TestClient(app, follow_redirects=False)


def test_flow():
    r = client.post("/companies", data={"name": "ООО «ПРИМЕР-СТРОЙ»", "inn": "7700000001", "sro_name": "Ассоциация «Пример»", "odo_level": "1"})
    assert r.status_code == 303
    cid = int(r.headers["location"].split("/")[-1])
    files = [("files", ("Контракт 7.txt", (FX / "contract_fiction.txt").read_bytes(), "text/plain")),
             ("files", ("ОС-02-02.txt", (FX / "estimate_fiction.txt").read_bytes(), "text/plain")),
             ("files", ("ССР.txt", (FX / "summary_fiction.txt").read_bytes(), "text/plain"))]
    r = client.post(f"/company/{cid}/contracts/new", files=files)
    assert r.status_code == 303
    ct = int(re.search(r"/contract/(\d+)/card", r.headers["location"]).group(1))
    page = client.get(f"/contract/{ct}/card").text
    assert "0100000000000000001-7" in page and "12200000.0" in page

    # сохранить карточку как есть (форма → расчёт)
    form = _form_from_card(ct)
    r = client.post(f"/contract/{ct}/card", data=form)
    assert r.status_code == 303 and r.headers["location"] == f"/contract/{ct}"
    page = client.get(f"/contract/{ct}").text.replace("\u00a0", " ")
    assert "Входит в ОДО" in page and "12 200 000,00" in page

    # решение
    r = client.post(f"/contract/{ct}/decision", data={"verdict": "agree", "by": "Тест", "note": "тестовый прогон"})
    assert r.status_code == 303
    page = client.get(f"/contract/{ct}").text
    assert "подтверждено" in page

    # реестр и выгрузки
    page = client.get(f"/company/{cid}").text.replace("\u00a0", " ")
    assert "12 200 000,00" in page and "занято" in page
    assert client.get(f"/company/{cid}/export.xlsx").status_code == 200
    assert client.get(f"/contract/{ct}/zaklyuchenie.docx").status_code == 200
    assert "Заключение" in client.get(f"/contract/{ct}/zaklyuchenie.md").text
    assert client.get(f"/company/{cid}/report").status_code == 200

    # письмо
    r = client.post(f"/contract/{ct}/letter/detect", data={"text": (FX / "letter_fiction.txt").read_text(encoding="utf-8")})
    assert r.status_code == 200 and "claim_type_0" in r.text
    n = int(re.search(r'id="claims_n" value="(\d+)"', r.text).group(1))
    data = {"text": "x", "claims_n": str(n), "letter_from": "ООО «ПРИМЕР-СТРОЙ»", "letter_summary": "просит исключить"}
    types = re.findall(r'name="claim_type_(\d+)">.*?<option value="(\w+)" selected', r.text, re.S)
    quotes = re.findall(r'name="claim_quote_(\d+)" rows="2">(.*?)</textarea>', r.text, re.S)
    for i, typ in types:
        data[f"claim_type_{i}"] = typ
    for i, q in quotes:
        data[f"claim_quote_{i}"] = q
    r = client.post(f"/contract/{ct}/letter/analyze", data=data)
    assert r.status_code == 303
    lid = int(r.headers["location"].split("/")[-1])
    page = client.get(f"/letter/{lid}").text
    assert "Проект ответа" in page and "Основание" in page
    assert client.get(f"/letter/{lid}/otvet.docx").status_code == 200

    # справочники
    assert client.get("/laws?q=55.8").status_code == 200
    assert client.get("/cases").status_code == 200
    assert client.get("/settings").status_code == 200


def _form_from_card(ct):
    """Собираем POST так, как его отправил бы браузер с предзаполненной формы."""
    from server import db
    c = db.contract(ct)["card"]
    k = c["contract"]
    f = {"number": k["number"], "date": k["date"] or "", "kind": k["kind"], "status": k["status"], "price_rub": str(k["price_rub"]),
         "price_includes_vat": "true", "period_from": k["period_from"] or "", "period_to": k["period_to"] or "", "subject_text": k["subject_text"],
         "kind_basis": k["kind_basis"] or "", "price_basis": k["price_basis"] or "", "status_basis": k["status_basis"] or "",
         "procurement": k["procurement"], "procurement_law": k["procurement_law"] or "null", "procurement_basis": k["procurement_basis"] or "",
         "nmck_rub": "", "nmck_basis": "", "executed_rub": "", "executed_basis": "", "has_final_act": "null", "termination_document": "",
         "addenda_n": "0", "member_name": c["member"]["name"], "member_inn": c["member"]["inn"] or "", "member_role": "contractor",
         "member_is_state_entity": "false", "member_sro_kinds": "build", "membership_date": "",
         "customer_name": c["customer"]["name"], "customer_inn": c["customer"]["inn"] or "", "customer_kind": c["customer"]["kind"], "customer_kind_basis": c["customer"]["kind_basis"] or "",
         "object_name": c["object"]["name"], "object_address": c["object"]["address"] or "", "cadastral": "", "work_type": c["work_type"],
         "is_capital": "true", "permit_required": "false", "category": "ordinary", "housing_type": "none", "object_basis": c["object"]["basis"] or "",
         "works_n": str(len(c["works"])), "as_of": "2026-09-23", "notes": ""}
    for i, w in enumerate(c["works"]):
        f[f"work_name_{i}"] = w["name"]
        f[f"work_amount_{i}"] = str(w["amount_rub"])
        f[f"work_source_{i}"] = w["source"] or ""
        f[f"work_human_{i}"] = ""
    return f
