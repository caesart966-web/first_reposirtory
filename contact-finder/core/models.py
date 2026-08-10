"""Модели данных: компания, контакт, результат работы коннектора.

Все объекты сериализуются в dict/JSON для хранения в SQLite и экспорта в XLSX.
"""
from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


def now_iso() -> str:
    """Текущее время в UTC в формате ISO-8601 (для полей «дата сбора»)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class SourceLevel(str, enum.Enum):
    """Уровень источника по приоритету достоверности (см. ТЗ, раздел 3)."""

    A = "A"  # официальные API и открытые госреестры
    B = "B"  # сайт самой компании
    C = "C"  # агрегаторы и справочники с официальным API
    D = "D"  # поисковый подбор домена (требует верификации)


class ContactType(str, enum.Enum):
    """Тип контакта."""

    EMAIL = "email"
    PHONE = "phone"
    WEBSITE = "website"
    SOCIAL = "social"
    MESSENGER = "messenger"


class CompanyStatus(str, enum.Enum):
    """Статус обработки компании в очереди."""

    PENDING = "pending"
    DONE = "done"
    RETRY_LATER = "retry_later"
    ERROR = "error"


@dataclass
class Contact:
    """Один найденный контакт из одного источника (до кросс-сверки)."""

    type: ContactType
    value: str                      # нормализованное значение (+7..., lower-email)
    raw: str = ""                   # как встретился в источнике
    source: str = ""                # имя коннектора
    source_url: Optional[str] = None
    level: SourceLevel = SourceLevel.D
    confidence: int = 0
    is_primary: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
    collected_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value
        d["level"] = self.level.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Contact":
        return cls(
            type=ContactType(d["type"]),
            value=d["value"],
            raw=d.get("raw", ""),
            source=d.get("source", ""),
            source_url=d.get("source_url"),
            level=SourceLevel(d.get("level", "D")),
            confidence=int(d.get("confidence", 0)),
            is_primary=bool(d.get("is_primary", False)),
            extra=d.get("extra") or {},
            collected_at=d.get("collected_at") or now_iso(),
        )


@dataclass
class ContactOrigin:
    """Откуда пришёл контакт (для листа «Источники» и кросс-сверки)."""

    source: str
    source_url: Optional[str]
    level: SourceLevel
    collected_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_url": self.source_url,
            "level": self.level.value,
            "collected_at": self.collected_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ContactOrigin":
        return cls(
            source=d["source"],
            source_url=d.get("source_url"),
            level=SourceLevel(d.get("level", "D")),
            collected_at=d.get("collected_at") or now_iso(),
        )


@dataclass
class MergedContact:
    """Контакт после объединения дубликатов из разных источников."""

    type: ContactType
    value: str
    raw: str
    origins: list[ContactOrigin] = field(default_factory=list)
    confidence: int = 0
    is_primary: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def sources(self) -> list[str]:
        seen: list[str] = []
        for o in self.origins:
            if o.source not in seen:
                seen.append(o.source)
        return seen

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "value": self.value,
            "raw": self.raw,
            "origins": [o.to_dict() for o in self.origins],
            "confidence": self.confidence,
            "is_primary": self.is_primary,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MergedContact":
        return cls(
            type=ContactType(d["type"]),
            value=d["value"],
            raw=d.get("raw", ""),
            origins=[ContactOrigin.from_dict(o) for o in d.get("origins", [])],
            confidence=int(d.get("confidence", 0)),
            is_primary=bool(d.get("is_primary", False)),
            extra=d.get("extra") or {},
        )


# Поля Company, которые коннекторы могут обновлять через company_updates
UPDATABLE_COMPANY_FIELDS = {
    "inn", "ogrn", "name_full", "name_short", "entity_status", "reg_date",
    "okved", "region", "address", "director_name", "director_position",
    "website", "website_verified", "website_candidate",
}


@dataclass
class Company:
    """Компания: входные данные + всё, что обогатили источники уровня A/C."""

    key: str                              # стабильный ключ (ИНН или суррогат)
    inn: Optional[str] = None
    ogrn: Optional[str] = None
    name_full: Optional[str] = None
    name_short: Optional[str] = None
    entity_status: Optional[str] = None   # «действующее» / «ликвидировано»
    reg_date: Optional[str] = None
    okved: Optional[str] = None
    region: Optional[str] = None
    address: Optional[str] = None
    director_name: Optional[str] = None
    director_position: Optional[str] = None
    website: Optional[str] = None         # подтверждённый сайт
    website_verified: bool = False        # на сайте найден ИНН / совпало название
    website_candidate: Optional[str] = None  # «предположительный» домен (уровень D)
    raw: dict[str, Any] = field(default_factory=dict)  # исходная строка входа

    @property
    def display_name(self) -> str:
        return self.name_short or self.name_full or self.raw.get("name") or self.inn or self.key

    @property
    def any_website(self) -> Optional[str]:
        return self.website or self.website_candidate

    def apply_updates(self, updates: dict[str, Any]) -> None:
        """Применить обновления полей от коннектора; не затирает данные пустыми."""
        for k, v in updates.items():
            if k not in UPDATABLE_COMPANY_FIELDS:
                continue
            if v is None or v == "":
                continue
            current = getattr(self, k, None)
            if k == "website_verified":
                # False не должен сбрасывать уже подтверждённый сайт
                if v:
                    self.website_verified = True
                continue
            # заполняем только пустые поля, кроме статуса/сайта — их можно уточнять
            if current in (None, "", False) or k in ("entity_status", "website", "website_candidate"):
                setattr(self, k, v)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Company":
        return cls(
            key=d["key"],
            inn=d.get("inn"),
            ogrn=d.get("ogrn"),
            name_full=d.get("name_full"),
            name_short=d.get("name_short"),
            entity_status=d.get("entity_status"),
            reg_date=d.get("reg_date"),
            okved=d.get("okved"),
            region=d.get("region"),
            address=d.get("address"),
            director_name=d.get("director_name"),
            director_position=d.get("director_position"),
            website=d.get("website"),
            website_verified=bool(d.get("website_verified", False)),
            website_candidate=d.get("website_candidate"),
            raw=d.get("raw") or {},
        )


@dataclass
class ConnectorResult:
    """Результат одного коннектора по одной компании."""

    contacts: list[Contact] = field(default_factory=list)
    company_updates: dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    error: Optional[str] = None
    retry_later: bool = False            # источник временно недоступен (429/5xx)
    source_urls: list[str] = field(default_factory=list)

    @classmethod
    def failed(cls, error: str, retry_later: bool = False) -> "ConnectorResult":
        return cls(ok=False, error=error, retry_later=retry_later)


def company_key_for(inn: Optional[str], name: Optional[str] = None,
                    region: Optional[str] = None, website: Optional[str] = None) -> str:
    """Стабильный ключ компании: ИНН, а без него — хэш от названия/сайта."""
    if inn:
        return inn.strip()
    basis = "|".join(x.strip().lower() for x in (name or "", region or "", website or ""))
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
    return f"noinn-{digest}"


def dumps(obj: Any) -> str:
    """JSON-сериализация без ASCII-экранирования (кириллица читаемой строкой)."""
    return json.dumps(obj, ensure_ascii=False)
