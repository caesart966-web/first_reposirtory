"""Детерминированный расчёт отклонений графика (production-копия).

Канонические формулы — .claude/skills/construction-control/references/deviation-logic.md.
Эта копия самодостаточна, чтобы MCP-сервер не зависел от файловой раскладки скилла.
Тест test_deviation.py фиксирует парность значений.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import config


def _d(x) -> date:
    return x if isinstance(x, date) else date.fromisoformat(str(x))


def planned_percent(start, finish, as_of) -> float:
    s, f, d = _d(start), _d(finish), _d(as_of)
    if f <= s:
        return 100.0 if d >= f else 0.0
    if d <= s:
        return 0.0
    if d >= f:
        return 100.0
    return round(100.0 * (d - s).days / (f - s).days, 1)


def deviation_percent(actual: float, planned: float) -> float:
    return round(actual - planned, 1)


def days_overdue(start, finish, actual: float, as_of) -> int:
    s, f, d = _d(start), _d(finish), _d(as_of)
    total = (f - s).days
    if total <= 0:
        return max((d - f).days, 0) if actual < 100 else 0
    planned_date = s + timedelta(days=round(actual / 100.0 * total))
    overdue = (d - planned_date).days
    if d > f and actual < 100:
        overdue = max(overdue, (d - f).days)
    return overdue


def forecast_finish(prev, cur):
    """prev/cur: {"date","actual"} | None -> (rate|None, forecast_iso|None)."""
    if not cur or not prev:
        return None, None
    d1, a1 = _d(prev["date"]), float(prev["actual"])
    d2, a2 = _d(cur["date"]), float(cur["actual"])
    days = (d2 - d1).days
    if days <= 0:
        return None, None
    rate = (a2 - a1) / days
    if rate <= 0:
        return round(rate, 3), None
    remaining = (100.0 - a2) / rate
    return round(rate, 3), (d2 + timedelta(days=round(remaining))).isoformat()


def sequence_violation(dep_type: str, a_task: float, a_pred: float) -> bool:
    dep_type = (dep_type or "FS").upper()
    if dep_type == "FS":
        return a_task > 0 and a_pred < 100
    if dep_type == "SS":
        return a_task > 0 and a_pred == 0
    if dep_type == "FF":
        return a_task >= 100 and a_pred < 100
    if dep_type == "SF":
        return a_task >= 100 and a_pred == 0
    return False


def status_flag(dev, as_of, finish, actual, start=None, pred_incomplete=False) -> str:
    d, f = _d(as_of), _d(finish)
    if start is not None and actual > 0 and (_d(start) > d or pred_incomplete):
        return "premature_start"
    if d > f and actual < 100:
        return "overdue"
    if dev > config.ON_TRACK_TOLERANCE_PP:
        return "ahead"
    if dev < -config.ON_TRACK_TOLERANCE_PP:
        return "behind"
    return "on_track"


def severity(is_hidden, flag, overdue, seq_violation, on_critical_path) -> str:
    if is_hidden and (seq_violation or flag in ("overdue", "premature_start")):
        return "critical"
    if on_critical_path and flag in ("overdue", "behind") and overdue > config.OVERDUE_DAYS_HIGH:
        return "critical"
    if flag == "overdue" or seq_violation or overdue > config.OVERDUE_DAYS_HIGH:
        return "high"
    if flag == "behind" or 1 <= overdue <= config.OVERDUE_DAYS_HIGH or flag == "premature_start":
        return "medium"
    if flag in ("on_track", "ahead"):
        return "info"
    return "low"


def evaluate_task(task: dict, obs: dict, as_of: str, prev_obs=None,
                  pred_incomplete=False, on_critical_path=False) -> dict:
    """Полная оценка задачи в помещении на дату обхода. Возвращает task_evaluation-дикт."""
    P = planned_percent(task["planned_start"], task["planned_finish"], as_of)
    A = float(obs["actual_percent"])
    dev = deviation_percent(A, P)
    overdue = days_overdue(task["planned_start"], task["planned_finish"], A, as_of)
    rate, forecast = forecast_finish(prev_obs, {"date": as_of, "actual": A})
    flag = status_flag(dev, as_of, task["planned_finish"], A,
                       start=task.get("planned_start"), pred_incomplete=pred_incomplete)
    sev = severity(bool(task.get("is_hidden_work")), flag, overdue,
                   pred_incomplete and A > 0, on_critical_path)
    conf = float(obs.get("confidence", 0.6))
    needs_human = sev == "critical" or conf < config.LOW_CONFIDENCE or bool(task.get("is_hidden_work"))
    return {
        "schedule_task_id": task["id"],
        "room_id": task.get("room_id") or obs.get("room_id"),
        "planned_percent": P,
        "actual_percent": A,
        "deviation_percent": dev,
        "days_overdue": overdue,
        "status_flag": flag,
        "forecast_finish": forecast,
        "progress_rate_pct_per_day": rate,
        "severity": sev,
        "confidence": conf,
        "requires_human_review": needs_human,
        "basis": (f"P={P}% (S={task['planned_start']}..F={task['planned_finish']}, D={as_of}); "
                  f"A={A}%; dev={dev}pp; overdue={overdue}d; flag={flag}"),
    }
