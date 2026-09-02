from core.models import (
    EXCLUDED_FROM_SRO,
    JOINED_SRO,
    SUSPENDED,
    TENDER_NO_SRO_BUILD_HIGH,
    TENDER_NO_SRO_DESIGN,
    Signal,
)
from core.scoring import priority_of, rescore_all, score_org, signal_points

TODAY = "2026-03-01"


def sig(t, d, src="nostroy"):
    return {"signal_type": t, "signal_date": d, "source": src}


def test_signal_points_modifiers(cfg):
    s = cfg["scoring"]
    assert signal_points(EXCLUDED_FROM_SRO, "2026-02-27", s, TODAY) == 130   # свежее 7 дней: x1.3
    assert signal_points(EXCLUDED_FROM_SRO, "2026-02-01", s, TODAY) == 100   # 28 дней: без модификатора
    assert signal_points(EXCLUDED_FROM_SRO, "2025-11-01", s, TODAY) == 50    # старше 90: x0.5
    assert signal_points(JOINED_SRO, "2026-02-27", s, TODAY) == 0


def test_priority_thresholds(cfg):
    s = cfg["scoring"]
    assert priority_of(100, s) == 1
    assert priority_of(99.9, s) == 2
    assert priority_of(60, s) == 2
    assert priority_of(59, s) == 3


def test_score_sum_and_multi_type_bonus(cfg):
    s = cfg["scoring"]
    r = score_org("1", [sig(SUSPENDED, "2026-02-01"), sig(TENDER_NO_SRO_BUILD_HIGH, "2026-02-10", "tenderguru")], s, TODAY)
    assert r.score == 70 + 80 + 30
    assert r.priority == 1
    assert r.types == [SUSPENDED, TENDER_NO_SRO_BUILD_HIGH]
    assert r.last_signal_date == "2026-02-10"
    # тот же тип дважды — бонуса нет
    r2 = score_org("1", [sig(SUSPENDED, "2026-02-01"), sig(SUSPENDED, "2026-02-02")], s, TODAY)
    assert r2.score == 140 and r2.priority == 1


def test_joined_later_suppresses_lead(cfg):
    s = cfg["scoring"]
    # исключён из НОСТРОЙ, потом вступил в другое СРО НОСТРОЙ — лид закрыт
    r = score_org("1", [sig(EXCLUDED_FROM_SRO, "2026-02-01"), sig(JOINED_SRO, "2026-02-15")], s, TODAY)
    assert r.score == 0 and r.suppressed == [EXCLUDED_FROM_SRO] and r.priority == 3
    # вступил в НОПРИЗ — строительный лид остаётся
    r = score_org("1", [sig(EXCLUDED_FROM_SRO, "2026-02-01"), sig(JOINED_SRO, "2026-02-15", "nopriz")], s, TODAY)
    assert r.score == 100
    # тендерный сигнал по проектированию закрывается вступлением в НОПРИЗ
    r = score_org("1", [sig(TENDER_NO_SRO_DESIGN, "2026-02-01", "tenderguru"), sig(JOINED_SRO, "2026-02-15", "nopriz")], s, TODAY)
    assert r.score == 0
    # joined раньше исключения — не мешает
    r = score_org("1", [sig(JOINED_SRO, "2026-01-01"), sig(EXCLUDED_FROM_SRO, "2026-02-01")], s, TODAY)
    assert r.score == 100
    s["suppress_if_joined_later"] = False
    r = score_org("1", [sig(EXCLUDED_FROM_SRO, "2026-02-01"), sig(JOINED_SRO, "2026-02-15")], s, TODAY)
    assert r.score == 100


def test_rescore_all_writes_orgs_and_outreach(cfg, db):
    db.add_signals([Signal("1000000001", EXCLUDED_FROM_SRO, "2026-02-01", "nostroy"),
                    Signal("1000000002", JOINED_SRO, "2026-02-01", "nostroy")])
    res = rescore_all(db, cfg, TODAY)
    assert res["1000000001"].score == 100 and res["1000000002"].score == 0
    assert db.get_org("1000000001").priority == 1
    assert db.outreach_map()["1000000001"]["status"] == "new"
