"""Базовый класс коннектора и реестр источников.

Плагинная структура: новый источник — это класс-наследник BaseConnector с
декоратором @register_connector. Оркестратор берёт список из реестра и
сортирует по приоритету из config.yaml — правка ядра не нужна.
"""
from __future__ import annotations

import abc
import difflib
import re
from typing import Any, Optional, Type

from core.config import Config
from core.models import Company, ConnectorResult, SourceLevel
from storage.db import Database
from utils.http import FetchError, HttpClient, RobotsDisallowed
from utils.logging_setup import get_logger

CONNECTOR_REGISTRY: dict[str, Type["BaseConnector"]] = {}


def register_connector(cls: Type["BaseConnector"]) -> Type["BaseConnector"]:
    """Декоратор регистрации коннектора в реестре."""
    CONNECTOR_REGISTRY[cls.name] = cls
    return cls


class BaseConnector(abc.ABC):
    """Общий контракт источника данных.

    Атрибуты класса:
        name             — машинное имя (ключ в config.yaml sources.*);
        title            — человекочитаемое название для логов и GUI;
        level            — уровень источника (A/B/C/D);
        default_priority — порядок обхода, меньше = раньше;
        needs_api_key    — имя переменной окружения с ключом (или None).
    """

    name: str = "base"
    title: str = "Базовый коннектор"
    level: SourceLevel = SourceLevel.D
    default_priority: int = 100
    needs_api_key: Optional[str] = None

    def __init__(self, http: HttpClient, config: Config, db: Database):
        self.http = http
        self.config = config
        self.db = db
        self.log = get_logger()

    # ------------------------------------------------------------------ #

    @property
    def priority(self) -> int:
        return self.config.source_priority(self.name, self.default_priority)

    @property
    def enabled(self) -> bool:
        if not self.config.source_enabled(self.name):
            return False
        if self.needs_api_key and not self.config.env(self.needs_api_key):
            return False
        return True

    def missing_key_note(self) -> Optional[str]:
        if self.needs_api_key and not self.config.env(self.needs_api_key):
            return f"нет ключа API ({self.needs_api_key} в .env)"
        return None

    def can_run(self, company: Company) -> bool:
        """Достаточно ли данных о компании для запроса к этому источнику."""
        return True

    @abc.abstractmethod
    async def fetch(self, company: Company) -> ConnectorResult:
        """Опросить источник. Может бросать FetchError — ловит safe_fetch."""

    async def safe_fetch(self, company: Company) -> ConnectorResult:
        """Обёртка: падение коннектора не роняет прогон (ТЗ, п. 9)."""
        try:
            return await self.fetch(company)
        except RobotsDisallowed as exc:
            self.log.info("[%s] %s: robots.txt запрещает доступ — источник пропущен",
                          company.key, self.title)
            return ConnectorResult.failed(f"robots.txt: {exc}", retry_later=False)
        except FetchError as exc:
            return ConnectorResult.failed(str(exc), retry_later=exc.retry_later)
        except Exception as exc:  # noqa: BLE001 — любой сбой изолируем
            self.log.exception("[%s] Сбой коннектора %s", company.key, self.name)
            return ConnectorResult.failed(f"{exc.__class__.__name__}: {exc}")

    # --- общие помощники для наследников ------------------------------- #

    @staticmethod
    def normalize_company_name(name: str) -> str:
        """Убрать ОПФ и кавычки для сравнения названий."""
        n = (name or "").lower()
        n = re.sub(
            r"\b(общество с ограниченной ответственностью|акционерное общество|"
            r"публичное акционерное общество|закрытое акционерное общество|"
            r"открытое акционерное общество|индивидуальный предприниматель|"
            r"ооо|ао|пао|зао|оао|ип|нко|анo|ано|фгуп|гуп|муп)\b",
            " ", n)
        n = re.sub(r"[«»\"'`]", " ", n)
        n = re.sub(r"[^\wа-яё ]", " ", n)
        return re.sub(r"\s+", " ", n).strip()

    @classmethod
    def names_similar(cls, a: Optional[str], b: Optional[str], threshold: float = 0.6) -> bool:
        na, nb = cls.normalize_company_name(a or ""), cls.normalize_company_name(b or "")
        if not na or not nb:
            return False
        if na in nb or nb in na:
            return True
        return difflib.SequenceMatcher(None, na, nb).ratio() >= threshold

    def company_query_name(self, company: Company) -> Optional[str]:
        return company.name_short or company.name_full or company.raw.get("name")


def walk_json_for_strings(obj: Any, key_filter: Optional[re.Pattern] = None,
                          _path: str = "") -> list[tuple[str, str]]:
    """Обойти произвольный JSON и вернуть пары (путь, строка).

    Используется коннекторами полуизвестных API: контакты ищутся по значению
    (регэкспом почты/телефона), а не по жёсткой схеме ответа.
    """
    found: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            found.extend(walk_json_for_strings(v, key_filter, f"{_path}.{k}" if _path else str(k)))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            found.extend(walk_json_for_strings(v, key_filter, f"{_path}[{i}]"))
    elif isinstance(obj, str):
        if key_filter is None or key_filter.search(_path):
            found.append((_path, obj))
    return found


def build_connectors(http: HttpClient, config: Config, db: Database,
                     only: Optional[set[str]] = None) -> list[BaseConnector]:
    """Создать включённые коннекторы, отсортированные по приоритету."""
    log = get_logger()
    connectors: list[BaseConnector] = []
    for name, cls in CONNECTOR_REGISTRY.items():
        if only is not None and name not in only:
            continue
        instance = cls(http, config, db)
        if not instance.enabled:
            note = instance.missing_key_note()
            if note:
                log.info("Источник «%s» отключён: %s", instance.title, note)
                db.set_source_state(name, 0, None, unavailable=True, note=note)
            continue
        connectors.append(instance)
    connectors.sort(key=lambda c: c.priority)
    return connectors
