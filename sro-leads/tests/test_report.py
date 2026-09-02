import run
from core.models import RegistryRow, SnapshotMeta
from core.report import snapshot_report


def row(inn, status, code=None, status_date=None, reg_date=None, sro="СРО А"):
    return RegistryRow(inn=inn, sro_name=sro, status=status, status_code=code,
                       status_date=status_date, reg_date=reg_date, name=f"ООО {inn}")


def test_report_says_backfill_applicable(cfg, db, capsys):
    rows = [
        row("1000000001", "Является членом", "1", reg_date="2020-01-01"),
        row("1000000002", "Является членом", "1", reg_date="2021-06-15"),
        row("1000000003", "Исключен", "3", status_date="2026-04-20"),      # в окне 30
        row("1000000004", "Исключен", "3", status_date="2026-03-01"),      # в окне 90
        row("1000000005", "Право приостановлено", "2", status_date="2025-12-01"),  # в окне 180
        row("1000000006", "Исключен", "3", status_date="2024-01-01"),      # вне окон
    ]
    db.write_snapshot("nostroy", "2026-05-01", rows)
    db.write_snapshot_meta("nostroy", "2026-05-01", SnapshotMeta(declared_total=6, fetched_rows=6, pages_done=1))
    db.commit()
    ok, rep = snapshot_report(db, cfg, "nostroy")
    assert ok
    assert "== Снапшот nostroy за 2026-05-01" in rep and "записей: 6" in rep
    assert "полный" in rep
    assert "Исключен" in rep and "50.0%" in rep                 # 3 из 6 — код 3
    assert "из них лидовых (исключены или приостановлены): 4" in rep
    assert "заполнена у 4 из 6" in rep and "min 2024-01-01, max 2026-04-20" in rep
    assert "ВЕРДИКТ: backfill применим, в окне 90 дней 2 записей" in rep
    assert "--backfill 90" in rep
    # окна: 30 дней -> 1 лидовая, 180 -> 3
    win = [l for l in rep.splitlines() if l.strip().startswith(("30 дней", "90 дней", "180 дней"))]
    assert win[0].split()[-1] == "1" and win[1].split()[-1] == "2" and win[2].split()[-1] == "3"
    assert "reg_date" in rep and "min 2020-01-01, max 2021-06-15" in rep
    # через run.py: код возврата 0, БД не меняется
    before = db.stats()
    assert run.print_snapshot_report(cfg, db, "nostroy", None) == 0
    assert db.stats() == before and "ВЕРДИКТ" in capsys.readouterr().out


def test_report_detects_active_only_slice(cfg, db):
    """Один статус на весь снапшот — API отдаёт срез действующих, backfill невозможен."""
    db.write_snapshot("nostroy", "2026-05-01", [row(f"100000000{i}", "Является членом", "1") for i in range(1, 5)])
    db.commit()
    ok, rep = snapshot_report(db, cfg, "nostroy")
    assert not ok
    assert "ВЕРДИКТ: API отдаёт срез действующих членов" in rep
    assert "статус один на весь снапшот (1)" in rep and "status_date пуста у всех записей" in rep
    assert "работаем через дифф" in rep
    assert "метаданных нет" in rep


def test_report_detects_empty_status_dates(cfg, db):
    """Статусы разные, но даты не пришли — backfill всё равно невозможен."""
    db.write_snapshot("nostroy", "2026-05-01", [row("1000000001", "Является членом", "1"),
                                                row("1000000002", "Исключен", "3")])
    db.commit()
    ok, rep = snapshot_report(db, cfg, "nostroy")
    assert not ok and "status_date пуста у всех записей" in rep
    assert "статус один на весь снапшот" not in rep


def test_report_flags_partial_and_uses_titles(cfg, db):
    cfg["registry"]["status_code_titles"] = {"3": "Членство прекращено"}
    db.write_snapshot("nostroy", "2026-05-01", [row("1000000001", "Является членом", "1"),
                                                row("1000000002", "Исключен", "3", status_date="2026-04-01")])
    db.write_snapshot_meta("nostroy", "2026-05-01",
                           SnapshotMeta(declared_total=100, fetched_rows=2, pages_done=1, broke_at_page=2, is_partial=True))
    db.commit()
    ok, rep = snapshot_report(db, cfg, "nostroy")
    assert ok and "Членство прекращено" in rep
    # страница обрыва живёт в логе, в snapshot_meta по ТЗ только признак частичности
    assert "ЧАСТИЧНЫЙ" in rep and "снапшот частичный" in rep and "--drop-snapshot nostroy --date 2026-05-01" in rep


def test_report_without_snapshot(cfg, db):
    ok, rep = snapshot_report(db, cfg, "nostroy")
    assert not ok and "Снапшотов источника «nostroy» в базе нет" in rep
    db.write_snapshot("nostroy", "2026-05-01", [row("1000000001", "Является членом", "1")])
    db.commit()
    ok, rep = snapshot_report(db, cfg, "nostroy", "2026-01-01")
    assert not ok and "Есть даты: 2026-05-01" in rep
