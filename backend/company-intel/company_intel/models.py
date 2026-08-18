"""Модель данных: запрос, находка, происхождение, итоговый профиль компании.

Главный принцип: любой факт (телефон, почта, адрес) хранится вместе с источником
(`Provenance`) и оценкой уверенности. Без ссылки на источник факт не считается
подтверждённым — его нельзя ни проверить, ни предъявить.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Iterable

# Виды находок. Значение всегда строка в нормализованном виде.
KINDS = (
    "name",        # наименование компании
    "inn", "ogrn", "kpp", "okpo",  # реквизиты
    "domain",      # домен (в т.ч. поддомены)
    "email",
    "phone",
    "address",
    "person",      # ФИО (+ должность в extra)
    "social",      # ссылка на соцсеть/мессенджер/каталог
    "url",         # прочая релевантная страница
    "fact",        # свободный факт: ОКВЭД, дата регистрации, уставный капитал...
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Provenance:
    """Откуда взят факт."""
    source: str                 # имя источника (website, egrul, crtsh...)
    url: str | None = None      # конкретная страница/эндпоинт
    fetched_at: str = field(default_factory=utcnow)
    note: str | None = None     # уточнение: «страница /contacts», «MX-запись»

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Finding:
    """Одна находка от одного источника."""
    kind: str
    value: str
    provenance: Provenance
    confidence: float = 0.5     # уверенность самого источника в этом значении
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"неизвестный вид находки: {self.kind}")
        self.confidence = max(0.0, min(1.0, float(self.confidence)))


@dataclass
class Attribute:
    """Слитое значение: одно и то же по нескольким источникам."""
    kind: str
    value: str
    confidence: float
    sources: list[Provenance] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def source_names(self) -> list[str]:
        seen: list[str] = []
        for p in self.sources:
            if p.source not in seen:
                seen.append(p.source)
        return seen

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "value": self.value,
            "confidence": round(self.confidence, 3),
            "sources": [p.to_dict() for p in self.sources],
        }
        if self.extra:
            d["extra"] = self.extra
        return d


@dataclass
class Query:
    """Всё, что пользователь знает о компании на входе.

    Любое поле может быть пустым: пайплайн раскручивает клубок от того, что есть.
    """
    name: str | None = None
    inn: str | None = None
    ogrn: str | None = None
    domain: str | None = None
    email: str | None = None
    phone: str | None = None
    person: str | None = None
    city: str | None = None
    country: str = "ru"
    extra_terms: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any([self.name, self.inn, self.ogrn, self.domain,
                        self.email, self.phone, self.person])

    def terms(self) -> list[str]:
        """Поисковые термины для поисковых движков."""
        out = [t for t in (self.name, self.inn, self.ogrn, self.domain,
                           self.email, self.phone, self.person) if t]
        out.extend(self.extra_terms)
        return out


@dataclass
class Profile:
    """Итог работы пайплайна."""
    query: Query
    attributes: dict[str, list[Attribute]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=utcnow)
    finished_at: str | None = None

    def get(self, kind: str) -> list[Attribute]:
        return self.attributes.get(kind, [])

    def values(self, kind: str, min_confidence: float = 0.0) -> list[str]:
        return [a.value for a in self.get(kind) if a.confidence >= min_confidence]

    def best(self, kind: str) -> Attribute | None:
        items = self.get(kind)
        return items[0] if items else None

    def all_attributes(self) -> Iterable[Attribute]:
        for kind in KINDS:
            yield from self.attributes.get(kind, [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": {k: v for k, v in asdict(self.query).items() if v},
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "stats": self.stats,
            "warnings": self.warnings,
            "attributes": {
                kind: [a.to_dict() for a in items]
                for kind, items in self.attributes.items() if items
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
