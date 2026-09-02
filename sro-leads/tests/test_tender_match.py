from datetime import datetime

from openpyxl import Workbook

from collectors.tender_match import TenderMatch, parse_money
from core.models import (
    TENDER_NO_SRO_BUILD_HIGH,
    TENDER_NO_SRO_BUILD_MID,
    TENDER_NO_SRO_DESIGN,
    RegistryRow,
)
from core.utils import resolve_path


def test_parse_money():
    assert parse_money("12 345 678,90 руб.") == 12345678.90
    assert parse_money("1,234,567.00") == 1234567.0
    assert parse_money(5000000) == 5000000.0
    assert parse_money("") is None
    assert parse_money(float("nan")) is None


def make_xlsx(path, rows, title_row=True):
    wb = Workbook()
    ws = wb.active
    if title_row:
        ws.append(["Выгрузка контрактов TenderGuru"])  # заголовок не в первой строке
    ws.append(["№", "Дата заключения", "Заказчик", "ИНН заказчика", "Поставщик", "ИНН поставщика",
               "Цена контракта", "ОКПД2", "Предмет контракта", "Ссылка"])
    for r in rows:
        ws.append(r)
    wb.save(path)


def test_tender_match_end_to_end(cfg, db):
    in_dir = resolve_path(cfg, "tenderguru_dir")
    processed = resolve_path(cfg, "tenderguru_processed_dir")
    # свежие снапшоты: 1000000001 — член НОСТРОЙ, 1000000005 — член НОПРИЗ
    db.write_snapshot("nostroy", "2026-01-01", [RegistryRow("1000000001", "СРО А", status="Является членом"),
                                                 RegistryRow("1000000009", "СРО А", status="Исключен")])
    db.write_snapshot("nopriz", "2026-01-01", [RegistryRow("1000000005", "СРО П", status="Является членом")])
    db.commit()
    make_xlsx(in_dir / "mail_1231_1_contracts.xlsx", [
        [1, datetime(2026, 1, 10), "Заказчик 1", "7800000001", "ООО Строй", "1000000001", "15 000 000", "41.20", "Стройка", "http://z/1"],   # член НОСТРОЙ — не лид
        [2, "12.01.2026", "Заказчик 1", "7800000001", "ООО Крыша", "1000000002", 15000000, "43.99.90", "Кровля", "http://z/2"],              # build_high
        [3, "12.01.2026", "Заказчик 2", "7800000002", "ООО Ремонт", "1000000003", 7000000, "41.20", "Ремонт", "http://z/3"],                 # build_mid
        [4, "12.01.2026", "Заказчик 2", "7800000002", "ООО Мелочь", "1000000004", 1000000, "41.20", "Ремонт", "http://z/4"],                 # < 5 млн — ничего
        [5, "13.01.2026", "Заказчик 3", "7800000003", "ООО Проект", "1000000005", 300000, "71.12", "Проект", "http://z/5"],                  # член НОПРИЗ — не лид
        [6, "13.01.2026", "Заказчик 3", "7800000003", "ООО Проект2", "1000000006", 300000, "71.12.12", "Изыскания", "http://z/6"],           # design, любая сумма
        [7, "13.01.2026", "Заказчик 3", "7800000003", "ООО Бывший", "1000000009", 20000000, "42.11", "Дорога", "http://z/7"],                # исключён — лид
        [8, "13.01.2026", "Заказчик 4", "7800000004", "ООО Пусто", None, 20000000, "42.11", "Дорога", "http://z/8"],                          # нет ИНН
        [9, "13.01.2026", "Заказчик 4", "7800000004", "ООО Мебель", "1000000007", 20000000, "31.01", "Мебель", "http://z/9"],                # не по теме
    ])
    c = TenderMatch(cfg, db)
    signals = c.collect()
    got = {(s.inn, s.signal_type, s.signal_date) for s in signals}
    assert got == {
        ("1000000002", TENDER_NO_SRO_BUILD_HIGH, "2026-01-12"),
        ("1000000003", TENDER_NO_SRO_BUILD_MID, "2026-01-12"),
        ("1000000006", TENDER_NO_SRO_DESIGN, "2026-01-13"),
        ("1000000009", TENDER_NO_SRO_BUILD_HIGH, "2026-01-13"),
    }
    by_inn = {s.inn: s for s in signals}
    assert by_inn["1000000002"].raw["sum"] == 15000000.0
    assert by_inn["1000000002"].raw["customer_inn"] == "7800000001"
    assert by_inn["1000000002"].url == "http://z/2"
    # файл переезжает в processed только после finalize (т.е. после записи в БД)
    assert (in_dir / "mail_1231_1_contracts.xlsx").exists()
    c.finalize()
    assert not (in_dir / "mail_1231_1_contracts.xlsx").exists()
    assert (processed / "mail_1231_1_contracts.xlsx").exists()


def test_tender_match_requires_snapshot(cfg, db):
    in_dir = resolve_path(cfg, "tenderguru_dir")
    make_xlsx(in_dir / "a.xlsx", [[1, "12.01.2026", "З", "7800000001", "П", "1000000002", 15000000, "41.20", "Стройка", ""]])
    assert TenderMatch(cfg, db).collect() == []          # снапшота нет — сигналов нет
    cfg["tenderguru"]["require_registry_snapshot"] = False
    sigs = TenderMatch(cfg, db).collect()
    assert [s.inn for s in sigs] == ["1000000002"]


def test_tender_match_no_files(cfg, db):
    assert TenderMatch(cfg, db).collect() == []
