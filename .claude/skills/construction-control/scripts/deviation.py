#!/usr/bin/env python3
"""Расчёт отклонений графика для Schedule Control Agent.

Все значения — обычная арифметика по датам и процентам (не оценки LLM).
Формулы описаны в references/deviation-logic.md.

Использование как библиотеки:
    from deviation import evaluate_task, planned_percent, days_overdue
Либо как CLI (демо):
    python3 deviation.py --demo
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Optional
import argparse
import json

# Пороги по умолчанию (конфигурируемы на уровне проекта).
ON_TRACK_TOLERANCE_PP = 5.0     # ± процентных пункта = «в графике»
OVERDUE_DAYS_HIGH = 7           # days_overdue выше -> severity high
LOW_CONFIDENCE = 0.5


def _d(x) -> date:
    return x if isinstance(x, date) else date.fromisoformat(str(x))


def planned_percent(start, finish, as_of) -> float:
    """§1 Плановая готовность на дату as_of (линейная модель)."""
    s, f, d = _d(start), _d(finish), _d(as_of)
    if f <= s:
        return 100.0 if d >= f else 0.0
    if d <= s:
        return 0.0
    if d >= f:
        return 100.0
    return round(100.0 * (d - s).days / (f - s).days, 1)


def deviation_percent(actual: float, planned: float) -> float:
    """§2 Отклонение факт-план (минус = отставание)."""
    return round(actual - planned, 1)


def days_overdue(start, finish, actual: float, as_of) -> int:
    """§3 Просрочка в днях через дату, к которой план ожидал факт `actual`."""
    s, f, d = _d(start), _d(finish), _d(as_of)
    total = (f - s).days
    if total <= 0:
        return max((d - f).days, 0) if actual < 100 else 0
    date_planned_for_actual = s + timedelta(days=round(actual / 100.0 * total))
    overdue = (d - date_planned_for_actual).days
    # Гарантия минимальной просрочки при пропущенном финише.
    if d > f and actual < 100:
        overdue = max(overdue, (d - f).days)
    return overdue


def forecast_finish(prev, cur):
    """§4 Прогноз завершения по темпу между двумя обходами.

    prev, cur: dict|None вида {"date": iso, "actual": float}.
    Возвращает (rate_pct_per_day|None, forecast_date_iso|None).
    """
    if not cur:
        return None, None
    if not prev:
        return None, None
    d1, a1 = _d(prev["date"]), float(prev["actual"])
    d2, a2 = _d(cur["date"]), float(cur["actual"])
    days = (d2 - d1).days
    if days <= 0:
        return None, None
    rate = (a2 - a1) / days
    if rate <= 0:
        return round(rate, 3), None  # работа стоит/регресс -> риск, на человека
    remaining_days = (100.0 - a2) / rate
    return round(rate, 3), (d2 + timedelta(days=round(remaining_days))).isoformat()


def sequence_violation(dep_type: str, a_task: float, a_pred: float) -> bool:
    """§7 Нарушение технологической последовательности."""
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


def status_flag(dev: float, as_of, finish, actual: float,
                start=None, pred_incomplete: bool = False) -> str:
    """§5-6 Флаг статуса."""
    d, f = _d(as_of), _d(finish)
    if start is not None and actual > 0 and (_d(start) > d or pred_incomplete):
        return "premature_start"
    if d > f and actual < 100:
        return "overdue"
    if dev > ON_TRACK_TOLERANCE_PP:
        return "ahead"
    if dev < -ON_TRACK_TOLERANCE_PP:
        return "behind"
    return "on_track"


def severity(is_hidden: bool, flag: str, overdue: int,
             seq_violation: bool, on_critical_path: bool) -> str:
    """§9 Критичность (эвристика)."""
    if is_hidden and (seq_violation or flag in ("overdue", "premature_start")):
        return "critical"
    if on_critical_path and flag in ("overdue", "behind") and overdue > OVERDUE_DAYS_HIGH:
        return "critical"
    if flag == "overdue" or seq_violation or overdue > OVERDUE_DAYS_HIGH:
        return "high"
    if flag == "behind" or 1 <= overdue <= OVERDUE_DAYS_HIGH or flag == "premature_start":
        return "medium"
    if flag in ("on_track", "ahead"):
        return "info"
    return "low"


@dataclass
class TaskEvaluation:
    schedule_task_id: str
    room_id: Optional[str]
    planned_percent: float
    actual_percent: float
    deviation_percent: float
    days_overdue: int
    status_flag: str
    forecast_finish: Optional[str]
    progress_rate_pct_per_day: Optional[float]
    severity: str
    confidence: float
    requires_human_review: bool
    basis: str


def evaluate_task(task: dict, obs: dict, as_of: str,
                  prev_obs: Optional[dict] = None,
                  pred_incomplete: bool = False,
                  on_critical_path: bool = False) -> TaskEvaluation:
    """Полная оценка одной задачи в одном помещении на дату обхода.

    task: {id, planned_start, planned_finish, is_hidden_work, dependency_type, room_id?}
    obs:  {actual_percent, confidence}
    prev_obs: {date, actual} | None
    """
    P = planned_percent(task["planned_start"], task["planned_finish"], as_of)
    A = float(obs["actual_percent"])
    dev = deviation_percent(A, P)
    overdue = days_overdue(task["planned_start"], task["planned_finish"], A, as_of)
    rate, forecast = forecast_finish(prev_obs, {"date": as_of, "actual": A})
    flag = status_flag(dev, as_of, task["planned_finish"], A,
                       start=task.get("planned_start"), pred_incomplete=pred_incomplete)
    if flag == "premature_start":
        pass  # уже учтён
    sev = severity(bool(task.get("is_hidden_work")), flag, overdue,
                   pred_incomplete and A > 0, on_critical_path)
    conf = float(obs.get("confidence", 0.6))
    needs_human = (sev == "critical") or conf < LOW_CONFIDENCE or bool(task.get("is_hidden_work"))
    basis = (f"P={P}% (S={task['planned_start']}..F={task['planned_finish']}, "
             f"D={as_of}); A={A}%; dev={dev}pp; overdue={overdue}d; flag={flag}")
    return TaskEvaluation(
        schedule_task_id=task["id"], room_id=task.get("room_id"),
        planned_percent=P, actual_percent=A, deviation_percent=dev,
        days_overdue=overdue, status_flag=flag, forecast_finish=forecast,
        progress_rate_pct_per_day=rate, severity=sev, confidence=conf,
        requires_human_review=needs_human, basis=basis,
    )


def _demo():
    task = {
        "id": "task_014", "planned_start": "2026-06-01", "planned_finish": "2026-07-01",
        "is_hidden_work": False, "dependency_type": "FS", "room_id": "room_0305",
    }
    obs = {"actual_percent": 40, "confidence": 0.72}
    prev = {"date": "2026-06-24", "actual": 25}
    ev = evaluate_task(task, obs, as_of="2026-07-01", prev_obs=prev,
                       pred_incomplete=False, on_critical_path=True)
    print(json.dumps(asdict(ev), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Расчёт отклонений графика")
    ap.add_argument("--demo", action="store_true", help="показать пример расчёта")
    args = ap.parse_args()
    if args.demo:
        _demo()
    else:
        ap.print_help()
