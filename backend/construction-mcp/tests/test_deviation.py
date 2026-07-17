from construction_mcp import deviation as dev


def test_planned_percent_linear():
    assert dev.planned_percent("2026-06-01", "2026-07-01", "2026-05-01") == 0.0
    assert dev.planned_percent("2026-06-01", "2026-07-01", "2026-08-01") == 100.0
    assert dev.planned_percent("2026-06-01", "2026-07-01", "2026-06-16") == 50.0


def test_deviation_and_overdue():
    assert dev.deviation_percent(40, 100) == -60.0
    # факт 40% при плане с 01.06 по 01.07, дата 01.07 -> отставание ~18 дней
    assert dev.days_overdue("2026-06-01", "2026-07-01", 40, "2026-07-01") == 18


def test_forecast():
    rate, forecast = dev.forecast_finish({"date": "2026-06-24", "actual": 25},
                                         {"date": "2026-07-01", "actual": 40})
    assert round(rate, 2) == 2.14
    assert forecast == "2026-07-29"
    # стоящая работа -> прогноза нет
    rate2, forecast2 = dev.forecast_finish({"date": "2026-06-24", "actual": 40},
                                           {"date": "2026-07-01", "actual": 40})
    assert forecast2 is None


def test_sequence_violation():
    assert dev.sequence_violation("FS", a_task=30, a_pred=80) is True
    assert dev.sequence_violation("FS", a_task=30, a_pred=100) is False


def test_evaluate_task_matches_skill_demo():
    ev = dev.evaluate_task(
        {"id": "task_014", "planned_start": "2026-06-01", "planned_finish": "2026-07-01",
         "is_hidden_work": False, "room_id": "room_0305"},
        {"actual_percent": 40, "confidence": 0.72}, as_of="2026-07-01",
        prev_obs={"date": "2026-06-24", "actual": 25}, on_critical_path=True)
    assert ev["deviation_percent"] == -60.0
    assert ev["days_overdue"] == 18
    assert ev["severity"] == "critical"
    assert ev["forecast_finish"] == "2026-07-29"
    assert ev["requires_human_review"] is True


def test_hidden_work_sequence_is_critical():
    ev = dev.evaluate_task(
        {"id": "t", "planned_start": "2026-06-01", "planned_finish": "2026-07-01",
         "is_hidden_work": True},
        {"actual_percent": 20, "confidence": 0.9}, as_of="2026-06-15",
        pred_incomplete=True)
    assert ev["severity"] == "critical"
    assert ev["requires_human_review"] is True
