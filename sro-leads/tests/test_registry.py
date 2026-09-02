import gzip
import json

import pytest

import collectors.base as base
from collectors.base import CollectorError, RegistryCollector, classify_status, diff_snapshots
from collectors.nostroy_registry import NostroyRegistry
from core.models import EXCLUDED_FROM_SRO, JOINED_SRO, SUSPENDED, RegistryRow

CLASSES = {"excluded": ["исключ"], "suspended": ["приостанов"], "active": ["действ", "является членом"]}


def test_classify_status():
    assert classify_status("Является членом", CLASSES) == "active"
    assert classify_status("Исключен", CLASSES) == "excluded"
    assert classify_status("Право приостановлено", CLASSES) == "suspended"
    assert classify_status(None, CLASSES) == "unknown"


def row(inn, sro="СРО А", status="Является членом"):
    return RegistryRow(inn=inn, sro_name=sro, status=status, reg_number="1", name=f"ООО {inn}")


def test_diff_generates_expected_signals():
    prev = [row("1"), row("2"), row("3"), row("4", status="Исключен"), row("5", "СРО А")]
    new = [
        row("2", status="Исключен"),              # исключён
        row("3", status="Право приостановлено"),   # приостановлен
        row("4", status="Исключен"),              # был исключён — ничего нового
        row("5", "СРО А", status="Исключен"), row("5", "СРО Б"),  # переехал в другое СРО — не лид
        row("6"),                                  # новый
    ]                                              # "1" пропал совсем
    sigs = diff_snapshots(prev, new, CLASSES, "nostroy", "2026-01-02")
    got = {(s.inn, s.signal_type) for s in sigs}
    assert got == {("1", EXCLUDED_FROM_SRO), ("2", EXCLUDED_FROM_SRO), ("3", SUSPENDED), ("6", JOINED_SRO)}
    # даты события в записях нет — берётся дата снапшота, event_date пустой, detected_by=diff
    assert all(s.signal_date == "2026-01-02" and s.source == "nostroy" and s.detected_by == "diff"
               and s.raw["event_date"] is None for s in sigs)


def test_diff_uses_event_dates_from_records():
    prev = [row("1"), row("2")]
    new = [RegistryRow("1", "СРО А", status="Исключен", status_date="2026-01-20"),
           RegistryRow("2", "СРО А", status="Право приостановлено", status_date="2026-01-21"),
           RegistryRow("3", "СРО А", status="Является членом", reg_date="2026-01-15")]
    sigs = {(s.inn, s.signal_type): s for s in diff_snapshots(prev, new, CLASSES, "nostroy", "2026-02-01")}
    assert sigs[("1", EXCLUDED_FROM_SRO)].signal_date == "2026-01-20"
    assert sigs[("2", SUSPENDED)].signal_date == "2026-01-21"
    assert sigs[("3", JOINED_SRO)].signal_date == "2026-01-15"
    assert sigs[("1", EXCLUDED_FROM_SRO)].raw["event_date"] == "2026-01-20"


def test_diff_restored_member_counts_as_joined():
    prev = [row("1", status="Право приостановлено")]
    new = [row("1")]
    sigs = diff_snapshots(prev, new, CLASSES, "nostroy", "2026-01-02")
    assert [(s.inn, s.signal_type) for s in sigs] == [("1", JOINED_SRO)]


class FakeCollector(NostroyRegistry):
    """Подменяем сетевой запрос: pages -> ответы API."""

    pages: list[list[dict]] = []
    bodies: list[dict] = []

    def _request(self, endpoint, page):
        FakeCollector.bodies.append(self._page_body(page))
        items = self.pages[page - 1] if page - 1 < len(self.pages) else []
        return {"success": True, "data": {"data": items, "total": sum(len(p) for p in self.pages)}}


def api_item(inn, status="Является членом", sro_id=7, sro="СРО Строителей"):
    return {"id": int(inn) * 10, "inn": inn, "short_description": f"ООО {inn}", "registration_number": f"R-{inn}",
            "member_status": {"code": "x", "title": status}, "sro": {"id": sro_id, "short_description": sro}}


def run_day(cfg, db, day, pages, monkeypatch):
    monkeypatch.setattr(base, "today_str", lambda: day)
    FakeCollector.pages = pages
    c = FakeCollector(cfg, db)
    signals = c.collect()
    if c.snapshot:
        db.write_snapshot(c.snapshot.source, c.snapshot.snapshot_date, c.snapshot.rows)
    db.add_signals(signals)
    db.commit()
    return c, signals


def test_two_day_run_produces_diff_and_pagination(cfg, db, monkeypatch, tmp_path):
    cfg["registry"]["nostroy"]["page_size"] = 2
    FakeCollector.bodies = []
    day1 = [[api_item("1000000001"), api_item("1000000002")], [api_item("1000000003")]]
    c1, s1 = run_day(cfg, db, "2026-01-01", day1, monkeypatch)
    assert s1 == []                                   # первый снапшот сигналов не даёт
    assert c1.snapshot and len(c1.snapshot.rows) == 3
    assert FakeCollector.bodies[0]["pageCount"] == "2"  # грабли: pageCount строкой
    assert db.snapshot_size("nostroy", "2026-01-01") == 3
    raw = tmp_path / "data" / "snapshots" / "nostroy_2026-01-01.json.gz"
    assert raw.exists()
    assert len(json.loads(gzip.open(raw).read())) == 3
    assert c1.snapshot.rows[0].url == "https://reestr.nostroy.ru/reestr/clients/7/members/10000000010"

    day2 = [[api_item("1000000001"), api_item("1000000002", status="Исключен")],
            [api_item("1000000004")]]                   # 3 пропал, 2 исключён, 4 новый
    c2, s2 = run_day(cfg, db, "2026-01-02", day2, monkeypatch)
    got = {(s.inn, s.signal_type) for s in s2}
    assert got == {("1000000002", EXCLUDED_FROM_SRO), ("1000000003", EXCLUDED_FROM_SRO), ("1000000004", JOINED_SRO)}
    assert db.snapshot_size("nostroy", "2026-01-02") == 3

    # Повторный запуск в тот же день: снапшот есть — ничего не собираем и ложных диффов нет
    c3, s3 = run_day(cfg, db, "2026-01-02", [[]], monkeypatch)
    assert s3 == [] and c3.snapshot is None


def test_small_snapshot_is_api_failure(cfg, db, monkeypatch, tmp_path):
    day1 = [[api_item(str(1000000000 + i)) for i in range(1, 11)]]
    run_day(cfg, db, "2026-01-01", day1, monkeypatch)
    monkeypatch.setattr(base, "today_str", lambda: "2026-01-02")
    FakeCollector.pages = [[api_item("1000000001")]]  # 1 из 10 — сбой
    with pytest.raises(CollectorError):
        FakeCollector(cfg, db).collect()
    assert not db.has_snapshot("nostroy", "2026-01-02")
    assert (tmp_path / "data" / "snapshots" / "nostroy_2026-01-02.failed.json.gz").exists()


def test_signals_dedup_in_db(db):
    from core.models import Signal
    s = Signal("1000000001", EXCLUDED_FROM_SRO, "2026-01-02", "nostroy")
    assert db.add_signals([s, s]) == 1
    assert db.add_signals([s]) == 0


def test_per_sro_mode(cfg, db, monkeypatch):
    calls = []

    class PerSro(RegistryCollector):
        name = "x"
        source = "nostroy"

        def _request(self, endpoint, page):
            calls.append(endpoint)
            if endpoint == "/api/sro/list":
                return {"data": {"data": [{"id": 1, "short_description": "СРО-1"}, {"id": 2, "short_description": "СРО-2"}] if page == 1 else []}}
            sro_id = int(endpoint.split("/")[3])
            items = [{"id": sro_id * 100, "inn": f"10000000{sro_id:02d}", "member_status": {"title": "Является членом"}}] if page == 1 else []
            return {"data": {"data": items}}

    cfg["registry"]["nostroy"]["sro_list_endpoint"] = "/api/sro/list"
    cfg["registry"]["nostroy"]["members_endpoint"] = "/api/sro/{sro_id}/member/list"
    monkeypatch.setattr(base, "today_str", lambda: "2026-01-01")
    c = PerSro(cfg, db)
    c.collect()
    assert {r.inn for r in c.snapshot.rows} == {"1000000001", "1000000002"}
    assert {r.sro_name for r in c.snapshot.rows} == {"СРО-1", "СРО-2"}
    assert "/api/sro/1/member/list" in calls


# ------------------------------------------------------------------ backfill
def days_ago(n, today="2026-04-01"):
    from datetime import date, timedelta
    return (date.fromisoformat(today) - timedelta(days=n)).isoformat()


def api_item_dated(inn, status, status_date, **kw):
    it = api_item(inn, status, **kw)
    it["member_status_date"] = status_date
    return it


def test_backfill_window(cfg, db, monkeypatch):
    today = "2026-04-01"
    monkeypatch.setattr(base, "today_str", lambda: today)
    FakeCollector.pages = [[
        api_item_dated("1000000001", "Исключен", days_ago(10)),                      # в окне
        api_item_dated("1000000002", "Исключен", days_ago(200)),                     # старше 90 дней
        api_item_dated("1000000003", "Право приостановлено", days_ago(30) + "T00:00:00+03:00"),  # в окне, ISO с временем
        api_item_dated("1000000004", "Является членом", days_ago(5)),                # действующий — не лид
        api_item_dated("1000000005", "Исключен", None),                              # без даты — пропуск
        api_item_dated("1000000006", "Исключен", days_ago(90)),                      # ровно на границе — в окне
        api_item_dated("1000000007", "Исключен", days_ago(3), sro_id=1, sro="СРО А"),
        api_item_dated("1000000007", "Является членом", None, sro_id=2, sro="СРО Б"),  # переехал — не лид
    ]]
    c = FakeCollector(cfg, db)
    c.backfill_days = 90
    signals = c.collect()
    assert c.snapshot is not None and len(c.snapshot.rows) == 8          # снапшот пишется в любом режиме
    got = {(s.inn, s.signal_type, s.signal_date) for s in signals}
    assert got == {
        ("1000000001", EXCLUDED_FROM_SRO, days_ago(10)),
        ("1000000003", SUSPENDED, days_ago(30)),
        ("1000000006", EXCLUDED_FROM_SRO, days_ago(90)),
    }
    assert all(s.raw["mode"] == "backfill" and s.raw["event_date"] == s.signal_date for s in signals)

    # снапшот за сегодня уже есть: backfill идёт по строкам из БД, реестр не перекачивается
    db.write_snapshot(c.snapshot.source, c.snapshot.snapshot_date, c.snapshot.rows)
    db.commit()
    FakeCollector.pages = [[]]
    c2 = FakeCollector(cfg, db)
    c2.backfill_days = 20
    got2 = {(s.inn, s.signal_date) for s in c2.collect()}
    assert got2 == {("1000000001", days_ago(10))} and c2.snapshot is None


def test_backfill_fails_loudly_without_status_date(cfg, db, monkeypatch):
    monkeypatch.setattr(base, "today_str", lambda: "2026-04-01")
    FakeCollector.pages = [[api_item("1000000001", "Исключен"), api_item("1000000002")]]
    c = FakeCollector(cfg, db)
    c.backfill_days = 90
    with pytest.raises(CollectorError, match="backfill невозможен.*member_status_date.*registry.nostroy.fields"):
        c.collect()
    cfg["registry"]["nostroy"]["fields"].pop("status_date")
    c = FakeCollector(cfg, db)
    c.backfill_days = 90
    with pytest.raises(CollectorError, match="fields.status_date"):
        c.collect()


def test_snapshot_keeps_status_date_and_migrates(cfg, db, monkeypatch):
    monkeypatch.setattr(base, "today_str", lambda: "2026-04-01")
    it = api_item_dated("1000000001", "Исключен", "2026-03-20")
    it["registry_registration_date"] = "2020-05-01"
    FakeCollector.pages = [[it]]
    c = FakeCollector(cfg, db)
    c.collect()
    db.write_snapshot("nostroy", "2026-04-01", c.snapshot.rows)
    r = db.snapshot_rows("nostroy", "2026-04-01")[0]
    assert r.status_date == "2026-03-20" and r.reg_date == "2020-05-01" and r.status_code == "x"
    # миграция старой БД без новых колонок
    db.conn.execute("CREATE TABLE old(snapshot_date TEXT, source TEXT, inn TEXT, sro_name TEXT, reg_number TEXT, status TEXT, name TEXT, url TEXT)")
    db.conn.execute("DROP TABLE registry_snapshots")
    db.conn.execute("ALTER TABLE old RENAME TO registry_snapshots")
    db._migrate()
    cols = {row["name"] for row in db.conn.execute("PRAGMA table_info(registry_snapshots)").fetchall()}
    assert {"status_code", "status_date", "reg_date"} <= cols


def test_backfill_then_diff_gives_one_signal_row(cfg, db, monkeypatch):
    """Один и тот же лид виден и backfill'ом, и диффом: в signals ровно одна строка."""
    # День 1: компания действующая
    run_day(cfg, db, "2026-03-01", [[api_item("1000000001"), api_item("1000000002")]], monkeypatch)
    # День 2: исключена с датой события 2026-03-02; сначала backfill, затем обычный дифф
    day2 = [[api_item_dated("1000000001", "Исключен", "2026-03-02"), api_item("1000000002")]]
    monkeypatch.setattr(base, "today_str", lambda: "2026-03-03")
    FakeCollector.pages = day2
    c = FakeCollector(cfg, db)
    c.backfill_days = 30
    bf = c.collect()
    assert [(s.inn, s.signal_date, s.detected_by) for s in bf] == [("1000000001", "2026-03-02", "backfill")]
    db.write_snapshot(c.snapshot.source, c.snapshot.snapshot_date, c.snapshot.rows)
    assert db.add_signals(bf) == 1
    db.commit()
    # Дифф на тех же данных (снапшот за 03-03 уже есть — эмулируем прогон диффа следующим днём с тем же реестром)
    _, diff = run_day(cfg, db, "2026-03-04", day2, monkeypatch)
    assert diff == []                      # исключение уже было в снапшоте 03-03 — дифф не повторяет
    # А если дифф увидел исключение первым, а backfill пришёл потом — тоже одна строка
    run_day(cfg, db, "2026-03-05", [[api_item("1000000003"), api_item("1000000002")]], monkeypatch)
    day6 = [[api_item_dated("1000000003", "Исключен", "2026-03-06"), api_item("1000000002")]]
    _, diff6 = run_day(cfg, db, "2026-03-06", day6, monkeypatch)
    assert [(s.inn, s.signal_date, s.detected_by) for s in diff6] == [("1000000003", "2026-03-06", "diff")]
    c = FakeCollector(cfg, db)
    c.backfill_days = 30
    assert db.add_signals(c.collect()) == 0   # backfill по снапшоту из БД: те же (inn, type, date) — дубля нет
    rows = db.conn.execute("SELECT inn, signal_date, detected_by FROM signals WHERE signal_type != 'joined_sro' ORDER BY inn").fetchall()
    assert [tuple(r) for r in rows] == [("1000000001", "2026-03-02", "backfill"), ("1000000003", "2026-03-06", "diff")]
