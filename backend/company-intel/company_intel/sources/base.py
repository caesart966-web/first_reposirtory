"""Интерфейс источника и контекст прогона.

Источник — это плагин: получает то, что уже известно о компании, и возвращает
список находок. Он не решает, верить ли себе, и не пишет в общий профиль —
только отдаёт `Finding` со своим происхождением.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..config import Config
from ..http import Fetcher
from ..models import Attribute, Finding, Provenance, Query

log = logging.getLogger("company_intel.sources")


@dataclass
class Context:
    """Общее состояние прогона, доступное источникам."""
    query: Query
    config: Config
    fetcher: Fetcher
    known: dict[str, list[Attribute]] = field(default_factory=dict)  # что уже найдено
    round: int = 0

    def known_values(self, kind: str, min_confidence: float = 0.35) -> list[str]:
        return [a.value for a in self.known.get(kind, []) if a.confidence >= min_confidence]

    def domains(self, min_confidence: float = 0.35) -> list[str]:
        """Домены компании: из запроса и найденные, запрос — первым."""
        out: list[str] = []
        if self.query.domain:
            out.append(self.query.domain)
        for value in self.known_values("domain", min_confidence):
            if value not in out:
                out.append(value)
        return out

    def inn(self) -> str | None:
        if self.query.inn:
            return self.query.inn
        values = self.known_values("inn", 0.5)
        return values[0] if values else None

    def names(self) -> list[str]:
        out = [self.query.name] if self.query.name else []
        for value in self.known_values("name", 0.4):
            if value not in out:
                out.append(value)
        return out

    def persons(self) -> list[str]:
        return self.known_values("person", 0.4)


class Source:
    """База для источников. Наследник задаёт метаданные и реализует `run`."""

    name: str = "source"
    title: str = "Источник"
    reliability: float = 0.5          # базовое доверие к источнику (0..1)
    needs_keys: tuple[str, ...] = ()  # переменные окружения, без которых не работает
    legal_note: str = ""              # особенности использования

    def available(self, config: Config) -> tuple[bool, str]:
        if not config.is_enabled(self.name):
            return False, "отключён настройками"
        missing = [k for k in self.needs_keys if not config.key(k)]
        if missing:
            return False, "нет ключей: " + ", ".join(missing)
        return True, ""

    def input_signature(self, ctx: Context) -> str:
        """Отпечаток входных данных. Если он не изменился — источник не перезапускают."""
        return "|".join(ctx.domains() + ctx.names() + [ctx.inn() or ""])

    async def run(self, ctx: Context) -> list[Finding]:  # pragma: no cover - интерфейс
        raise NotImplementedError

    # -- помощники для наследников -----------------------------------------

    def prov(self, url: str | None = None, note: str | None = None) -> Provenance:
        return Provenance(source=self.name, url=url, note=note)

    def finding(
        self, kind: str, value: str, *, url: str | None = None, note: str | None = None,
        confidence: float | None = None, **extra: Any,
    ) -> Finding:
        return Finding(
            kind=kind,
            value=value,
            provenance=self.prov(url, note),
            confidence=self.reliability if confidence is None else confidence,
            extra={k: v for k, v in extra.items() if v not in (None, "", [], {})},
        )
