"""Модели данных. Один лид = один ИНН (строкой, всегда)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# Типы сигналов. Веса — в config.yaml (scoring.weights).
EXCLUDED_FROM_SRO = "excluded_from_sro"
SUSPENDED = "suspended"
JOINED_SRO = "joined_sro"
TENDER_NO_SRO_DESIGN = "tender_no_sro_design"
TENDER_NO_SRO_BUILD_HIGH = "tender_no_sro_build_high"
TENDER_NO_SRO_BUILD_MID = "tender_no_sro_build_mid"

SIGNAL_TITLES = {
    EXCLUDED_FROM_SRO: "Исключён из СРО",
    SUSPENDED: "Членство приостановлено",
    JOINED_SRO: "Вступил в СРО",
    TENDER_NO_SRO_DESIGN: "Закупка (проектирование) без СРО",
    TENDER_NO_SRO_BUILD_HIGH: "Закупка (стройка >10 млн) без СРО",
    TENDER_NO_SRO_BUILD_MID: "Закупка (стройка 5–10 млн) без СРО",
}

# Статусы обзвона (таблица outreach).
OUTREACH_STATUSES = ("new", "called", "in_progress", "won", "dead")


@dataclass
class Signal:
    """Событие-сигнал по организации. Уникальность: (inn, signal_type, signal_date)."""

    inn: str
    signal_type: str
    signal_date: str  # YYYY-MM-DD
    source: str       # nostroy | nopriz | tenderguru | ...
    url: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)

    def raw_json(self) -> str:
        return json.dumps(self.raw, ensure_ascii=False, default=str)


@dataclass
class Org:
    inn: str
    ogrn: Optional[str] = None
    name: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    okved: Optional[str] = None
    site: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    director: Optional[str] = None
    status: Optional[str] = None      # ACTIVE | LIQUIDATING | LIQUIDATED | BANKRUPT | REORGANIZING | None
    enriched_at: Optional[str] = None
    score: Optional[float] = None     # считается в scoring.py, хранится для экспорта и отбора на обогащение
    priority: Optional[int] = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RegistryRow:
    """Одна запись снапшота реестра."""

    inn: str
    sro_name: str
    reg_number: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    status_code: Optional[str] = None   # код статуса членства из API (registry.<src>.fields.status_code)
    status_date: Optional[str] = None   # дата прекращения/приостановки, YYYY-MM-DD (fields.status_date)
    reg_date: Optional[str] = None      # дата регистрации в реестре (fields.reg_date)


@dataclass
class Snapshot:
    """Снапшот реестра за дату, который оркестратор записывает в БД."""

    source: str
    snapshot_date: str
    rows: list[RegistryRow]
