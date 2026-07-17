from construction_mcp import parsers


def test_read_xlsx_and_schedule(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Наименование работ", "Начало", "Окончание", "Ответственный"])
    ws.append(["Штукатурка стен", "01.06.2026", "01.07.2026", "ООО Отделка"])
    ws.append(["Стяжка пола", "2026-06-10", "2026-06-20", "ООО Полы"])
    path = tmp_path / "schedule.xlsx"
    wb.save(path)

    raw = parsers.read_xlsx(str(path))
    assert raw["error"] is None and raw["sheets"]

    sched = parsers.read_schedule(str(path))
    assert sched["error"] is None
    assert len(sched["tasks"]) == 2
    t0 = sched["tasks"][0]
    assert t0["name"].startswith("Штукатурка")
    assert t0["planned_start"] == "2026-06-01"
    assert t0["planned_finish"] == "2026-07-01"
    assert sched["tasks"][1]["planned_start"] == "2026-06-10"


def test_read_missing_file():
    assert parsers.read_pdf("/nope/x.pdf")["error"]
    assert parsers.read_docx("/nope/x.docx")["error"]
