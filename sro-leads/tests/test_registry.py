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
    assert all(s.signal_date == "2026-01-02" and s.source == "nostroy" for s in sigs)


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
