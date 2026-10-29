"""Разбор договора и смет правилами — на вымышленных текстах."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.parse_contract import build_card, parse_contract_text, parse_estimates  # noqa: E402
from server.letters import detect_claims, letter_meta  # noqa: E402
from server import engine  # noqa: E402

FX = ROOT / "tests" / "fixtures"


def read(name):
    return (FX / name).read_text(encoding="utf-8")


def test_contract_fields():
    f, h = parse_contract_text(read("contract_fiction.txt"))
    assert f["number"] == "0100000000000000001-7"
    assert f["date"] == "2026-05-18"
    assert f["price_rub"] == 12_200_000.0 and f["price_includes_vat"] is True
    assert f["customer_inn"] == "7700000000"
    assert f["customer_name"].startswith("ГБОУ")
    assert f["contractor_name"] == "ООО «ПРИМЕР-СТРОЙ»"
    assert f["procurement"] == "competitive" and f["procurement_law"] == "44-fz"
    assert "протокол № 0100000000000000001 от 05.05.2026" == f["protocol"]
    assert f["period_from"] == "2026-05-20" and f["period_to"] == "2026-09-30"
    assert f["okpd2"] == "43.99.90.190"
    assert "nmck_rub" not in f  # «10 процентов НМЦК» из раздела о штрафах — не сумма


def test_estimates():
    e = parse_estimates([read("estimate_fiction.txt"), read("summary_fiction.txt")])
    assert [x["amount_rub"] for x in e["lines"]] == [2_000_000.0, 6_600_000.0, 1_400_000.0]
    assert e["object_total"] == 10_000_000.0 and e["lines_sum"] == 10_000_000.0
    assert e["summary_total"] == 12_200_000.0 and e["summary_header_total"] == 12_200_000.0
    assert e["methodology_421"] and e["vat_pct"] == 22 and e["unforeseen_pct"] == 2


def test_card_valid_and_assessed():
    docs = [{"filename": "contract.docx", "kind": "contract", "text": read("contract_fiction.txt")},
            {"filename": "os.pdf", "kind": "estimate", "text": read("estimate_fiction.txt")},
            {"filename": "ssr.pdf", "kind": "estimate", "text": read("summary_fiction.txt")}]
    card, meta = build_card({"name": "ООО «ПРИМЕР-СТРОЙ»", "inn": "7700000001"}, docs)
    assert engine.validate_card(card) == []
    assert card["work_type"] == "capital_repair" and card["customer"]["kind"] == "operator"
    assert meta["needs_review"] == []
    a, md = engine.assess_card(card, find_cases=False)
    assert (a["verdict"]["membership_required"], a["verdict"]["counts_for_odo"]) == ("yes", "yes")
    assert a["verdict"]["amount_total_rub"] == 12_200_000.0
    assert "Заключение по договору" in md


def test_below_threshold_card():
    t = read("contract_fiction.txt").replace("12200000 рублей 00 копеек", "8200000 рублей 00 копеек")
    card, meta = build_card({"name": "ООО «ПРИМЕР-СТРОЙ»", "inn": None}, [{"filename": "c.docx", "kind": "contract", "text": t}])
    assert any("начальная цена" in w.lower() for w in meta["warnings"])
    a, _ = engine.assess_card(card, find_cases=False)
    assert (a["verdict"]["membership_required"], a["verdict"]["counts_for_odo"]) == ("no", "no")


def test_letter_claims():
    t = read("letter_fiction.txt")
    types = [c["type"] for c in detect_claims(t)]
    assert "customer_not_developer" in types or "state_exempt" in types
    assert "works_not_in_list" in types and "executed" in types
    m = letter_meta(t)
    assert m["date"] == "2026-09-01" and m["contract_number"] == "0100000000000000001-7"


def test_design_contract_fields_and_sro_kind():
    """Проектный договор: цена из «Стоимость работ … составляет», вид — проектирование (капремонт в предмете называет объект),
    без признаков торгов — прямой с пометкой «проверить», «единственный поставщик» из приказа Минстроя в ТЗ не считается."""
    f, h = parse_contract_text(read("design_fiction.txt"))
    assert f["number"] == "0001-ПД" and f["date"] == "2026-09-01"
    assert f["price_rub"] == 2_450_000.0 and f["price_includes_vat"] is True
    assert f["work_type"] == "design"
    assert f["procurement"] == "direct" and f.get("procurement_inferred") is True and "признаков" in h["procurement"]
    assert f["period_to"] == "2027-02-20"
    assert f["customer_name"] == "АО «ПРИМЕР-ТЕПЛО»"
    docs = [{"filename": "d.pdf", "kind": "contract", "text": read("design_fiction.txt")}]
    card, meta = build_card({"name": "ООО «ПСК «ПРИМЕР»", "inn": "7700000003", "sro_kinds": ["build"]}, docs)
    assert engine.validate_card(card) == []
    assert card["contract"]["kind"] == "design" and card["object"]["is_capital"] is True
    assert "procurement" in meta["needs_review"]
    a, md = engine.assess_card(card, find_cases=False)
    v = a["verdict"]
    assert v["sro_kind"] == "design" and v["in_member_sro"] is False and v["counts_for_odo"] == "no"
    assert any(x["title"] == "Вид СРО по договору" for x in a["findings"])
    assert "СРО проектировщиков" in v["summary"] and "СРО строителей" in v["summary"]
    # член состоит и в СРО проектировщиков — замечания о чужом виде нет, прямой договор в ОДО всё равно не входит
    card2, _ = build_card({"name": "ООО «ПСК «ПРИМЕР»", "inn": "7700000003", "sro_kinds": ["build", "design"]}, docs)
    a2, _ = engine.assess_card(card2, find_cases=False)
    assert a2["verdict"]["in_member_sro"] is True and a2["verdict"]["counts_for_odo"] == "no"
    assert not any(x["title"] == "Вид СРО по договору" for x in a2["findings"])


def test_survey_customer_circle_is_narrower():
    """Ч. 2 ст. 47: у изыскателей заказчики — застройщик и техзаказчик; эксплуатант и регоператор членства не требуют."""
    docs = [{"filename": "d.pdf", "kind": "contract", "text": read("design_fiction.txt")}]
    card, _ = build_card({"name": "ООО «ПСК «ПРИМЕР»", "inn": "7700000003", "sro_kinds": ["survey"]}, docs)
    card["contract"]["kind"] = "survey"
    card["work_type"] = "survey"
    card["customer"]["kind"] = "operator"
    a, _ = engine.assess_card(card, find_cases=False)
    assert a["verdict"]["membership_required"] == "no" and a["verdict"]["counts_for_odo"] == "no"
    assert "ч. 2 ст. 47" in a["verdict"]["summary"]
    card["customer"]["kind"] = "developer"
    a, _ = engine.assess_card(card, find_cases=False)
    assert a["verdict"]["membership_required"] == "yes"   # прямой договор: членство есть, в ОДО не входит
    assert a["verdict"]["counts_for_odo"] == "no"


def test_state_road_contract():
    """Госконтракт Росавтодора на «ремонт» путепровода: ИКЗ в скобках, объект из шапки, имя заказчика с кавычками внутри,
    дата из реквизитов приложения, срок «завершение СМР», дата приказа не принимается за начало работ, по смете — капремонт."""
    t = read("state_road_fiction.txt")
    f, h = parse_contract_text(t)
    assert f["number"] == "7/26/ПРИМ" and f.get("date") is None
    assert f["ikz"].startswith("2611234567890") and f["customer_inn"] == "1234567890"
    assert "Управление федеральных автомобильных дорог" in f["customer_name"] and not f["customer_name"].startswith("Федерального")
    assert f["contractor_name"] == "ООО «ПРИМЕР-МОСТ»"
    assert f["price_rub"] == 120_000_000.0 and f["procurement"] == "competitive" and f["procurement_law"] == "44-fz"
    assert f["object_name"].startswith("Ремонт путепровода") and f.get("period_from") is None and f["period_to"] == "2027-10-15"
    card, meta = build_card({"name": "ООО «ПРИМЕР-МОСТ»", "inn": "7700000009", "sro_kinds": ["build"]}, [{"filename": "k.docx", "kind": "contract", "text": t}])
    assert card["contract"]["date"] == "2026-08-25" and "приложений" in meta["hints"].get("date", "")
    assert card["work_type"] == "capital_repair" and "балок" in meta["hints"]["work_type"]
    assert card["customer"]["kind"] == "technical_customer" and card["object"]["name"].startswith("Ремонт путепровода")
    assert engine.validate_card(card) == []
    a, _ = engine.assess_card(card, find_cases=False)
    assert (a["verdict"]["membership_required"], a["verdict"]["counts_for_odo"]) == ("yes", "yes")
    assert a["verdict"]["amount_total_rub"] == 120_000_000.0
