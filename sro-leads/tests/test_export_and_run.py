import yaml
from openpyxl import load_workbook

import run
from core.export import build_export
from core.models import EXCLUDED_FROM_SRO, JOINED_SRO, SUSPENDED, TENDER_NO_SRO_DESIGN, Org, Signal
from core.scoring import rescore_all

TODAY = "2026-03-01"


def seed(db):
    db.add_signals([
        Signal("0105012345", EXCLUDED_FROM_SRO, "2026-02-27", "nostroy", "http://r/1", {"name": "ООО Ноль", "sro_name": "СРО А"}),
        Signal("1000000002", SUSPENDED, "2026-02-01", "nostroy", "http://r/2", {"name": "ООО Пауза"}),
        Signal("1000000003", TENDER_NO_SRO_DESIGN, "2026-02-10", "tenderguru", None, {"name": "ООО Проект", "sum": 1e6}),
        Signal("1000000004", EXCLUDED_FROM_SRO, "2026-02-01", "nostroy"),   # ликвидирован
        Signal("1000000005", EXCLUDED_FROM_SRO, "2026-02-01", "nostroy"),   # уже обзвонен
        Signal("1000000006", JOINED_SRO, "2026-02-01", "nostroy"),          # не лид
        Signal("1000000007", SUSPENDED, "2026-02-20", "nostroy", None, {"name": "ООО Спор", "event_date": "2026-02-20"}),
        Signal("1000000007", JOINED_SRO, "2026-02-25", "nostroy", None, {"event_date": None}),  # конфликт дат
    ])
    db.upsert_org(Org(inn="1000000004", name="ООО Труп", status="LIQUIDATED"))
    db.upsert_org(Org(inn="0105012345", region="г Санкт-Петербург", phone="+7 (812) 000-00-00"))
    rescore_all(db, {"scoring": yaml.safe_load(open("config.yaml", encoding="utf-8"))["scoring"]}, TODAY)
    db.set_outreach("1000000005", "called", "не берут трубку")
    db.commit()


def test_export_sheets_and_formats(cfg, db):
    seed(db)
    path = build_export(db, cfg, TODAY)
    assert path.name == "Лиды_2026-03-01.xlsx"
    wb = load_workbook(path)
    assert wb.sheetnames == ["Горячие", "Все лиды", "История сигналов"]
    ws = wb["Все лиды"]
    header = [c.value for c in ws[1]]
    assert header[:3] == ["Приоритет", "Скор", "ИНН"] and header[-2:] == ["Статус обзвона", "Комментарий"]
    inns = [ws.cell(row=r, column=3).value for r in range(2, ws.max_row + 1)]
    assert inns == ["0105012345", "1000000003", "1000000002", "1000000007"]  # по скору вниз (130, 90, 70, 70 — при равенстве по ИНН)
    conflict_col = header.index("Конфликт дат") + 1
    assert ws.cell(row=5, column=conflict_col).value == "да" and ws.cell(row=2, column=conflict_col).value is None
    c = ws.cell(row=2, column=3)
    assert c.number_format == "@" and isinstance(c.value, str)   # ИНН текстом, ведущий ноль на месте
    assert ws.cell(row=2, column=1).fill.fgColor.rgb.endswith("FFC7CE")  # приоритет 1 — красный
    assert ws.cell(row=3, column=1).fill.fgColor.rgb.endswith("FFEB9C")  # приоритет 2 — жёлтый
    assert ws.cell(row=2, column=4).value == "ООО Ноль"            # имя подтянулось из сигнала
    assert ws.cell(row=2, column=7).value == "Исключён из СРО"
    hot = wb["Горячие"]
    assert [hot.cell(row=r, column=3).value for r in range(2, hot.max_row + 1)] == ["0105012345"]
    hist = wb["История сигналов"]
    assert hist.max_row == 6 and "sro_name=СРО А" in hist.cell(row=2, column=8).value


def test_export_region_filter(cfg, db):
    seed(db)
    cfg["export"]["regions"] = ["Санкт-Петербург"]
    wb = load_workbook(build_export(db, cfg, TODAY))
    ws = wb["Все лиды"]
    assert [ws.cell(row=r, column=3).value for r in range(2, ws.max_row + 1)] == ["0105012345"]


def test_run_main_export_only_and_mark(tmp_path):
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    for k in cfg["paths"]:
        cfg["paths"][k] = str(tmp_path / cfg["paths"][k])
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    assert run.main(["--mark", "1000000001", "called", "перезвонить", "--config", str(cfg_path)]) == 0
    assert run.main(["--export-only", "--config", str(cfg_path)]) == 0
    assert list((tmp_path / "output").glob("Лиды_*.xlsx"))
    assert list((tmp_path / "logs").glob("*.log"))
    # неизвестный коллектор не роняет прогон
    assert run.main(["--only", "nope", "--no-enrich", "--config", str(cfg_path)]) == 0
