import run
from core.models import RegistryRow, SnapshotMeta
from core.report import inspect_orgs, snapshot_report, top_inns


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


# ------------------------------------------------------- ручная сверка лидов
def seed_inspect(db, cfg):
    from core.models import EXCLUDED_FROM_SRO, JOINED_SRO, TENDER_NO_SRO_DESIGN, Org, Signal
    from core.scoring import rescore_all
    db.add_signals([
        Signal("7802961682", EXCLUDED_FROM_SRO, "2026-04-20", "nostroy", "http://reestr/members/7",
               {"name": 'ООО "ГАЛЕОН"', "sro_name": "СРО А", "reg_number": "R-77", "status": "Исключен",
                "event_date": "2026-04-20"}, detected_by="backfill"),
        Signal("7802961682", TENDER_NO_SRO_DESIGN, "2026-04-25", "tenderguru", "http://zakupki/1",
               {"name": 'ООО "ГАЛЕОН"', "sum": 3000000.0, "okpd": "71.12"}, detected_by="file"),
        Signal("7800000002", EXCLUDED_FROM_SRO, "2026-04-10", "nostroy", None, {"event_date": "2026-04-10"}),
        Signal("7800000002", JOINED_SRO, "2026-04-15", "nostroy", None, {"event_date": None}),
    ])
    db.write_snapshot("nostroy", "2026-05-01", [
        RegistryRow("7802961682", "СРО А", reg_number="R-77", status="Исключен", status_code="3",
                    status_date="2026-04-20", reg_date="2019-03-01", name='ООО "ГАЛЕОН"',
                    url="http://reestr/members/7")])
    db.upsert_org(Org(inn="7802961682", name='ООО "ГАЛЕОН"', region="г Санкт-Петербург", okved="41.20",
                      site="https://galeon.ru/", site_verified="unverified", phone_unverified="+7 (812) 648-02-63",
                      director="Мухтаров Дмитрий Владимирович", enriched_at="2026-05-01 10:00:00"))
    rescore_all(db, cfg, "2026-05-01")
    db.commit()


def test_inspect_prints_everything_for_manual_check(cfg, db):
    seed_inspect(db, cfg)
    rep = inspect_orgs(db, cfg, ["7802961682"], "2026-05-01")
    assert '7802961682  ООО "ГАЛЕОН"' in rep
    assert "регион: г Санкт-Петербург" in rep and "ОКВЭД: 41.20" in rep
    assert "приоритет: 1" in rep and "обзвон: new" in rep
    # сигналы: тип, дата, источник, detected_by
    assert "[excluded_from_sro] 2026-04-20  источник nostroy  обнаружен backfill" in rep
    assert "[tender_no_sro_design] 2026-04-25  источник tenderguru  обнаружен file" in rep
    assert "ссылка из сигнала: http://zakupki/1" in rep
    assert '"okpd": "71.12"' in rep                       # raw_json в читаемом виде
    # запись снапшота и ссылки
    assert "nostroy за 2026-05-01: СРО А, рег.№ R-77" in rep
    assert "дата статуса 2026-04-20, дата регистрации 2019-03-01" in rep
    assert "карточка члена: http://reestr/members/7" in rep
    assert "nostroy: https://reestr.nostroy.ru/reestr?searchString=7802961682" in rep
    # контакты
    assert "сайт: https://galeon.ru/  (проверка: unverified)" in rep
    assert "с неподтверждённого сайта — телефон: +7 (812) 648-02-63" in rep
    assert "руководитель: Мухтаров Дмитрий Владимирович" in rep


def test_inspect_shows_date_conflict_and_missing(cfg, db):
    seed_inspect(db, cfg)
    rep = inspect_orgs(db, cfg, ["7800000002", "7800000009"], "2026-05-01")
    assert "ФЛАГ date_conflict" in rep
    assert "организация в снапшотах не найдена" in rep
    assert "7800000009: в базе нет ни организации, ни сигналов" in rep


def test_inspect_top_uses_export_filters(cfg, db):
    seed_inspect(db, cfg)
    assert top_inns(db, cfg, 10, "2026-05-01") == ["7802961682", "7800000002"]
    db.set_outreach("7802961682", "called")
    db.commit()
    assert top_inns(db, cfg, 10, "2026-05-01") == ["7800000002"]   # обзвонённые не берутся
    assert top_inns(db, cfg, 1, "2026-05-01") == ["7800000002"]


def test_inspect_writes_file(cfg, db, tmp_path, capsys):
    seed_inspect(db, cfg)
    out = tmp_path / "inspect.txt"
    assert run.inspect(cfg, db, ["7802961682"], None, str(out)) == 0
    assert 'ООО "ГАЛЕОН"' in out.read_text(encoding="utf-8")
    assert "Сохранено" in capsys.readouterr().out
    before = db.stats()
    assert run.inspect(cfg, db, [], 5, None) == 0
    assert db.stats() == before                                    # БД не меняется
    assert "7802961682" in capsys.readouterr().out
