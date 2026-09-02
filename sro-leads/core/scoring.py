"""Скоринг: веса и модификаторы из config.yaml, сумма по сигналам организации."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from .models import (
    EXCLUDED_FROM_SRO,
    JOINED_SRO,
    SUSPENDED,
    TENDER_NO_SRO_BUILD_HIGH,
    TENDER_NO_SRO_BUILD_MID,
    TENDER_NO_SRO_DESIGN,
)
from .utils import days_between, today_str

# Какой реестр «закрывает» потребность по типу сигнала (для отсечения уже вступивших).
NEED_SOURCE = {
    TENDER_NO_SRO_DESIGN: "nopriz",
    TENDER_NO_SRO_BUILD_HIGH: "nostroy",
    TENDER_NO_SRO_BUILD_MID: "nostroy",
}


@dataclass
class ScoreResult:
    inn: str
    score: float = 0.0
    priority: int = 3
    types: list[str] = field(default_factory=list)   # типы засчитанных сигналов
    last_signal_date: Optional[str] = None
    suppressed: list[str] = field(default_factory=list)  # типы, отсечённые из-за joined_sro
    date_conflict: bool = False  # есть joined_sro по тому же реестру, но даты сравнить нельзя — проверить вручную


def _get(sig: Any, key: str) -> Any:
    if isinstance(sig, Mapping):
        return sig.get(key)
    try:
        return sig[key]  # sqlite3.Row
    except (TypeError, IndexError, KeyError):
        return getattr(sig, key, None)


def event_date(sig: Any) -> Optional[str]:
    """Дата события сигнала. Для сигналов реестра — из raw.event_date (может отсутствовать),
    для остальных (тендеры, старые записи) — signal_date."""
    raw = _get(sig, "raw")
    if raw is None:
        raw_json = _get(sig, "raw_json")
        if raw_json:
            try:
                raw = json.loads(raw_json)
            except ValueError:
                raw = None
    if isinstance(raw, dict) and "event_date" in raw:
        return raw.get("event_date") or None
    return _get(sig, "signal_date") or None


def signal_points(signal_type: str, signal_date: str, scfg: dict[str, Any], today: Optional[str] = None) -> float:
    weight = float(scfg.get("weights", {}).get(signal_type, 0))
    if weight <= 0:
        return 0.0
    today = today or today_str()
    try:
        age = days_between(signal_date, today)
    except ValueError:
        age = 0
    if age <= int(scfg.get("fresh_days", 7)):
        weight *= float(scfg.get("fresh_multiplier", 1.3))
    elif age > int(scfg.get("stale_days", 90)):
        weight *= float(scfg.get("stale_multiplier", 0.5))
    return weight


def priority_of(score: float, scfg: dict[str, Any]) -> int:
    if score >= float(scfg.get("priority_1_min", 100)):
        return 1
    if score >= float(scfg.get("priority_2_min", 60)):
        return 2
    return 3


def score_org(inn: str, signals: list[Any], scfg: dict[str, Any], today: Optional[str] = None) -> ScoreResult:
    """Скор организации = сумма баллов по сигналам после модификаторов.

    Правило joined_sro: лидовый сигнал (исключение, приостановка, тендер без СРО) гасится
    только если по тому же реестру есть вступление с датой СТРОГО позже даты события лида.
    Компания, вступившая в январе и исключённая в марте, остаётся лидом. Если у одной из
    записей даты события нет, гасить нельзя: лид остаётся с флагом date_conflict.
    """
    today = today or today_str()
    res = ScoreResult(inn=inn)
    joined: dict[str, list[Optional[str]]] = {}  # source -> даты вступлений (None = даты нет)
    for s in signals:
        if _get(s, "signal_type") == JOINED_SRO:
            joined.setdefault(_get(s, "source") or "", []).append(event_date(s))
    suppress = bool(scfg.get("suppress_if_joined_later", True))

    total = 0.0
    types: set[str] = set()
    for s in signals:
        t = _get(s, "signal_type")
        d = _get(s, "signal_date") or ""
        if t == JOINED_SRO:
            continue
        need = NEED_SOURCE.get(t) if t in NEED_SOURCE else (_get(s, "source") or "")
        if suppress and joined.get(need):
            lead_date = event_date(s)
            dated = [j for j in joined[need] if j]
            if lead_date and dated and max(dated) > lead_date:
                res.suppressed.append(t)
                continue
            if not lead_date or len(dated) < len(joined[need]):
                res.date_conflict = True
        pts = signal_points(t, d, scfg, today)
        if pts <= 0:
            continue
        total += pts
        types.add(t)
        if res.last_signal_date is None or d > res.last_signal_date:
            res.last_signal_date = d
    if len(types) >= 2:
        total += float(scfg.get("multi_type_bonus", 30))
    res.score = round(total, 2)
    res.types = sorted(types)
    res.priority = priority_of(res.score, scfg)
    return res


def rescore_all(db: Any, cfg: dict[str, Any], today: Optional[str] = None) -> dict[str, ScoreResult]:
    scfg = cfg.get("scoring", {})
    by_inn = db.signals_by_inn()
    results: dict[str, ScoreResult] = {}
    for inn, sigs in by_inn.items():
        r = score_org(inn, sigs, scfg, today)
        results[inn] = r
        db.set_score(inn, r.score, r.priority)
        db.ensure_outreach(inn)
    db.commit()
    return results
