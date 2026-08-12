"""Структуры данных для результатов проверки СРО.

Главная идея файла — три возможных вердикта и жёсткое правило:
«нет» ставится ТОЛЬКО когда реестр реально ответил и ответ разобран однозначно.
Во всех остальных случаях — «не удалось проверить».
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from enum import Enum


class Verdict(str, Enum):
    """Что мы пишем в колонку «Есть СРО»."""

    YES = "да"
    NO = "нет"
    UNKNOWN = "не удалось проверить"


class Outcome(str, Enum):
    """Результат обращения к одному реестру.

    FOUND   — запись по этому ИНН найдена;
    EMPTY   — реестр ответил корректно, записей по ИНН нет (достоверное «нет»);
    UNKNOWN — не смогли получить или разобрать ответ (НЕ повод писать «нет»).
    """

    FOUND = "found"
    EMPTY = "empty"
    UNKNOWN = "unknown"


# Как называются реестры в отчёте
SOURCE_NOSTROY = "НОСТРОЙ"
SOURCE_NOPRIZ = "НОПРИЗ"

# Нормализованные статусы членства
STATUS_ACTIVE = "действует"
STATUS_SUSPENDED = "приостановлено"
STATUS_EXCLUDED = "исключён"
STATUS_UNCLEAR = ""  # не смогли распознать — пишем исходную формулировку реестра


def normalize_status(raw: str | None) -> str:
    """Свести формулировку реестра к одному из трёх статусов.

    Реестры пишут по-разному: «Является членом СРО», «Действующий»,
    «Исключен из реестра», «Приостановлено право осуществлять...».
    Разбираем по ключевым словам; если не узнали — возвращаем пустую строку,
    и вызывающий код подставит исходный текст как есть (не выдумываем).
    """
    if not raw:
        return STATUS_UNCLEAR
    text = str(raw).strip().lower().replace("ё", "е")
    if not text:
        return STATUS_UNCLEAR

    # Порядок важен: «исключён» и «приостановлено» проверяем до «действует»,
    # потому что строка вида «действие членства приостановлено» содержит оба слова.
    if re.search(r"исключ|прекращ|утрат|аннулир", text):
        return STATUS_EXCLUDED
    if re.search(r"приостанов|аостанов", text):
        return STATUS_SUSPENDED
    if re.search(r"действ|является членом|актив|включен|состоит", text):
        return STATUS_ACTIVE
    return STATUS_UNCLEAR


@dataclass
class Membership:
    """Одно найденное членство в СРО."""

    source: str  # НОСТРОЙ или НОПРИЗ
    sro_name: str | None = None
    registry_number: str | None = None
    status_raw: str | None = None
    # Название самой компании так, как оно записано в реестре. Нужно, чтобы
    # поймать опечатку в ИНН: запись найдётся, но про другую организацию.
    member_name: str | None = None

    @property
    def status(self) -> str:
        """Нормализованный статус; если не распознан — исходный текст реестра."""
        normalized = normalize_status(self.status_raw)
        if normalized:
            return normalized
        return (self.status_raw or "").strip()

    def to_dict(self) -> dict:
        data = asdict(self)
        data["status"] = self.status
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Membership":
        return cls(
            source=data.get("source", ""),
            sro_name=data.get("sro_name"),
            registry_number=data.get("registry_number"),
            status_raw=data.get("status_raw"),
            member_name=data.get("member_name"),
        )


@dataclass
class RegistryAnswer:
    """Ответ одного реестра по одному ИНН."""

    source: str
    outcome: Outcome
    memberships: list[Membership] = field(default_factory=list)
    note: str = ""  # диагностика: почему unknown / какой эндпоинт сработал

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "outcome": self.outcome.value,
            "memberships": [m.to_dict() for m in self.memberships],
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegistryAnswer":
        return cls(
            source=data.get("source", ""),
            outcome=Outcome(data.get("outcome", "unknown")),
            memberships=[Membership.from_dict(m) for m in data.get("memberships", [])],
            note=data.get("note", ""),
        )


# Что считать ответом «да» в колонке «Есть СРО»
BASIS_FOUND = "found"  # есть запись в реестре, любой статус
BASIS_ACTIVE = "active"  # только действующее членство


@dataclass
class CheckResult:
    """Итог по одной компании — то, что попадает в Excel."""

    inn: str
    checked_at: str = ""
    answers: list[RegistryAnswer] = field(default_factory=list)
    note: str = ""
    # Как трактовать найденную запись: см. BASIS_FOUND / BASIS_ACTIVE
    basis: str = BASIS_FOUND

    # ---------- сводные поля для Excel ----------

    # Действующее членство важнее прекращённого: компания может состоять
    # в одной СРО и быть исключённой из другой (обычное дело при смене СРО).
    _STATUS_ORDER = {STATUS_ACTIVE: 0, STATUS_SUSPENDED: 1, STATUS_EXCLUDED: 2}

    @property
    def memberships(self) -> list[Membership]:
        result: list[Membership] = []
        for answer in self.answers:
            result.extend(answer.memberships)
        # Сортировка устойчивая: внутри одного статуса порядок реестра сохраняется.
        # Нужна, чтобы в колонке «Название СРО» первой стояла действующая СРО,
        # а не та, из которой компанию исключили пять лет назад.
        return sorted(result, key=lambda m: self._STATUS_ORDER.get(m.status, 3))

    @property
    def verdict(self) -> Verdict:
        """Ключевое правило программы.

        «да»  — хотя бы один реестр нашёл запись по этому ИНН;
        «нет» — все опрошенные реестры ответили достоверно и ничего не нашли;
        «не удалось проверить» — во всех остальных случаях.

        Обратите внимание: одного UNKNOWN достаточно, чтобы вердикт стал
        «не удалось проверить». Мы сознательно предпочитаем «не знаю»
        ошибочному «нет».

        При basis=BASIS_ACTIVE «да» ставится только для действующего членства:
        исключённые и приостановленные получают «нет», но название СРО и статус
        всё равно записываются в файл — информация не теряется.
        """
        if any(a.outcome is Outcome.FOUND for a in self.answers):
            if self.basis != BASIS_ACTIVE:
                return Verdict.YES
            statuses = [m.status for m in self.memberships]
            if any(status == STATUS_ACTIVE for status in statuses):
                return Verdict.YES
            if statuses and all(
                status in (STATUS_SUSPENDED, STATUS_EXCLUDED) for status in statuses
            ):
                return Verdict.NO
            # Запись есть, но статус не распознан — выдумывать не будем.
            return Verdict.UNKNOWN
        if not self.answers:
            return Verdict.UNKNOWN
        if all(a.outcome is Outcome.EMPTY for a in self.answers):
            return Verdict.NO
        return Verdict.UNKNOWN

    @property
    def sro_names(self) -> str:
        return "; ".join(
            m.sro_name.strip() for m in self.memberships if m.sro_name and m.sro_name.strip()
        )

    @property
    def registry_numbers(self) -> str:
        return "; ".join(
            str(m.registry_number).strip()
            for m in self.memberships
            if m.registry_number and str(m.registry_number).strip()
        )

    @property
    def statuses(self) -> str:
        return "; ".join(m.status for m in self.memberships if m.status)

    @property
    def member_names(self) -> str:
        """Названия компании так, как их вернул реестр (без повторов)."""
        seen: list[str] = []
        for membership in self.memberships:
            name = (membership.member_name or "").strip()
            if name and name not in seen:
                seen.append(name)
        return "; ".join(seen)

    @property
    def sources(self) -> str:
        """Источник(и): где нашли запись, а если не нашли — где искали."""
        if self.memberships:
            names = [m.source for m in self.memberships if m.source]
        else:
            names = [a.source for a in self.answers if a.source]
        seen: list[str] = []
        for name in names:
            if name not in seen:
                seen.append(name)
        return "; ".join(seen)

    @property
    def diagnostics(self) -> str:
        """Короткое пояснение — попадает в колонку «Примечание»."""
        parts = [self.note] if self.note else []
        for answer in self.answers:
            if not answer.note:
                continue
            # Показываем пояснение, когда проверка не удалась, а также когда
            # запись нашли, но реквизиты СРО вытащить не смогли.
            unclear_hit = answer.outcome is Outcome.FOUND and not answer.memberships
            if answer.outcome is Outcome.UNKNOWN or unclear_hit:
                parts.append(f"{answer.source}: {answer.note}")
        return "; ".join(p for p in parts if p)

    def to_dict(self) -> dict:
        return {
            "inn": self.inn,
            "checked_at": self.checked_at,
            "note": self.note,
            "basis": self.basis,
            "answers": [a.to_dict() for a in self.answers],
            # Ниже — денормализованные поля, чтобы кэш можно было читать глазами
            "verdict": self.verdict.value,
            "sro_names": self.sro_names,
            "registry_numbers": self.registry_numbers,
            "statuses": self.statuses,
            "sources": self.sources,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CheckResult":
        return cls(
            inn=data.get("inn", ""),
            checked_at=data.get("checked_at", ""),
            note=data.get("note", ""),
            basis=data.get("basis", BASIS_FOUND),
            answers=[RegistryAnswer.from_dict(a) for a in data.get("answers", [])],
        )
