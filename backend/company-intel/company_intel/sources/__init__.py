"""Реестр источников. Добавить новый источник — значит добавить класс сюда."""
from __future__ import annotations

from ..config import Config
from .base import Context, Source
from .checko import CheckoSource
from .crtsh import CrtShSource
from .dadata import DaDataSource
from .dns_records import DnsSource
from .egrul import EgrulSource
from .email_guess import EmailGuessSource
from .hunter import HunterSource
from .rdap import RdapSource
from .search import SearchSource
from .twogis import TwoGisSource
from .website import WebsiteSource

# Порядок влияет только на вывод `sources`; исполняются они параллельно.
ALL_SOURCE_CLASSES = (
    DaDataSource, EgrulSource, CheckoSource, WebsiteSource, DnsSource,
    RdapSource, CrtShSource, SearchSource, TwoGisSource, HunterSource,
    EmailGuessSource,
)


def all_sources() -> list[Source]:
    return [cls() for cls in ALL_SOURCE_CLASSES]


def available_sources(config: Config) -> tuple[list[Source], list[tuple[str, str]]]:
    """Возвращает (готовые к работе источники, [(имя, причина отказа)])."""
    ready: list[Source] = []
    skipped: list[tuple[str, str]] = []
    for source in all_sources():
        ok, reason = source.available(config)
        (ready.append(source) if ok else skipped.append((source.name, reason)))
    return ready, skipped


def describe_sources(config: Config) -> list[dict]:
    rows = []
    for source in all_sources():
        ok, reason = source.available(config)
        rows.append({
            "name": source.name,
            "title": source.title,
            "reliability": source.reliability,
            "keys": list(source.needs_keys),
            "ready": ok,
            "reason": reason,
            "legal_note": source.legal_note,
        })
    return rows


__all__ = [
    "Context", "Source", "all_sources", "available_sources", "describe_sources",
    "CheckoSource", "CrtShSource", "DaDataSource", "DnsSource", "EgrulSource",
    "EmailGuessSource", "HunterSource", "RdapSource", "SearchSource",
    "TwoGisSource", "WebsiteSource",
]
