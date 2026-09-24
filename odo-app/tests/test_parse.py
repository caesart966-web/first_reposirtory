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
