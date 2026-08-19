"""
Клиент открытого Единого реестра НОСТРОЙ (reestr.nostroy.ru).

Зачем. Выгрузки, которые дают на вход скрипту, часто не содержат дат
вступления и исключения — а в самом реестре НОСТРОЙ они есть всегда и
публикуются бесплатно, без ключей. Страница reestr.nostroy.ru/sro/410 берёт
данные через внутренний JSON-API — этим же API пользуемся и мы: по ИНН члена
запрашиваем его запись и достаём даты и статус членства.

Формат ответа этого API нигде официально не описан и может меняться, поэтому
клиент устроен так же защитно, как клиент checko.ru:

* пробуются несколько известных вариантов запроса (POST со структурой
  фильтров и с простой поисковой строкой);
* разбор ответа не привязан к точным именам полей: любые ключи с датами
  классифицируются по смыслу (вступление/исключение), запись выбирается по
  совпадению ИНН;
* первый «сырой» ответ сохраняется в ``output/parsed/nostroy_api_sample.json``
  — если формат изменится, по нему видно, как он выглядит на самом деле;
* результаты кэшируются в файле состояния: повторные запуски не дёргают
  реестр по уже известным компаниям.
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import requests

from .config import Settings
from .logging_setup import get_logger
from .models import utcnow_iso
from .textutils import (
    clean_text,
    extract_emails,
    extract_fio,
    extract_phones,
    merge_unique,
    parse_date,
)

logger = get_logger("nostroy-api")

#: Базовый адрес реестра.
NOSTROY_BASE = "https://reestr.nostroy.ru"

#: Известные конечные точки поиска членов (пробуются по очереди).
_LIST_ENDPOINTS: tuple[str, ...] = (
    "/api/sro/all/member/list",
    "/api/member/list",
)

#: Ключи JSON, означающие дату вступления/регистрации в реестре.
_JOIN_KEY_RE = re.compile(
    r"(registr|accession|admission|join|вступ|включ|принят|регистрац)", re.IGNORECASE
)
#: Ключи JSON, означающие дату исключения/прекращения членства.
_EXIT_KEY_RE = re.compile(
    r"(exclu|terminat|stop|прекращ|исключ|окончан)", re.IGNORECASE
)
#: Ключи с датами, которые надо игнорировать (рождение, обновление записи и т.п.).
_IGNORE_KEY_RE = re.compile(
    r"(birth|created|updated|modif|check|insur|contract|approv|suspend|рожден|обновл)",
    re.IGNORECASE,
)
_DATE_KEY_RE = re.compile(r"(date|дата|_at$)", re.IGNORECASE)
_STATUS_KEY_RE = re.compile(r"status|статус", re.IGNORECASE)
_INN_KEY_RE = re.compile(r"^inn$|инн", re.IGNORECASE)
#: Ключи с контактами члена (телефон/почта/адрес/руководитель).
_PHONE_KEY_RE = re.compile(r"phone|tel|телефон", re.IGNORECASE)
_EMAIL_KEY_RE = re.compile(r"mail|почта", re.IGNORECASE)
_ADDRESS_KEY_RE = re.compile(r"address|адрес|place|location", re.IGNORECASE)
_DIRECTOR_KEY_RE = re.compile(r"director|руковод|head|исполнительн|фио|fio", re.IGNORECASE)


@dataclass(slots=True)
class NostroyMemberInfo:
    """Сведения о члене СРО из открытого реестра НОСТРОЙ."""

    inn: str = ""
    found: bool = False
    date_join: date | None = None
    date_exit: date | None = None
    status_text: str = ""            # статус членства как в реестре (текст)
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    directors: list[str] = field(default_factory=list)
    error: str = ""
    fetched_at: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "inn": self.inn,
            "found": self.found,
            "date_join": self.date_join.isoformat() if self.date_join else None,
            "date_exit": self.date_exit.isoformat() if self.date_exit else None,
            "status_text": self.status_text,
            "phones": self.phones,
            "emails": self.emails,
            "addresses": self.addresses,
            "directors": self.directors,
            "error": self.error,
            "fetched_at": self.fetched_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NostroyMemberInfo":
        return cls(
            inn=data.get("inn", ""),
            found=bool(data.get("found")),
            date_join=parse_date(data.get("date_join")),
            date_exit=parse_date(data.get("date_exit")),
            status_text=data.get("status_text", ""),
            phones=list(data.get("phones", [])),
            emails=list(data.get("emails", [])),
            addresses=list(data.get("addresses", [])),
            directors=list(data.get("directors", [])),
            error=data.get("error", ""),
            fetched_at=data.get("fetched_at", ""),
        )


# --------------------------------------------------------------------------- #
#                          Разбор JSON-ответа реестра                          #
# --------------------------------------------------------------------------- #

def _clean_date_value(value: Any) -> date | None:
    """Дата из значения поля (обрезаем часовой пояс ISO-строк)."""
    if isinstance(value, str):
        value = value.split("+")[0].replace("T", " ").strip()
    return parse_date(value)


def _collect_member_records(node: Any, out: list[dict[str, Any]]) -> None:
    """Рекурсивно собирает словари, похожие на запись члена (имеют ИНН)."""
    if isinstance(node, dict):
        has_inn = any(
            _INN_KEY_RE.search(str(key)) and re.fullmatch(r"\d{10}|\d{12}", re.sub(r"\D", "", str(value or "")))
            for key, value in node.items()
            if isinstance(value, (str, int))
        )
        if has_inn:
            out.append(node)
        for value in node.values():
            _collect_member_records(value, out)
    elif isinstance(node, list):
        for item in node:
            _collect_member_records(item, out)


def _record_inn(record: dict[str, Any]) -> str:
    for key, value in record.items():
        if isinstance(value, (str, int)) and _INN_KEY_RE.search(str(key)):
            digits = re.sub(r"\D", "", str(value))
            if len(digits) in (10, 12):
                return digits
    return ""


def parse_member_payload(payload: Any, inn: str) -> NostroyMemberInfo:
    """
    Достаёт из ответа реестра запись с нужным ИНН и её даты/статус.

    Не привязан к именам полей: даты классифицируются по смыслу ключа,
    среди нескольких записей выбирается точное совпадение ИНН.
    """
    info = NostroyMemberInfo(inn=inn, fetched_at=utcnow_iso())
    candidates: list[dict[str, Any]] = []
    _collect_member_records(payload, candidates)

    record = next((item for item in candidates if _record_inn(item) == inn), None)
    if record is None:
        info.error = "запись с таким ИНН не найдена в ответе реестра"
        return info

    info.found = True

    def status_text_of(value: Any) -> str:
        """Достаёт текст статуса из строки или вложенного объекта {id, title}."""
        if isinstance(value, str):
            return clean_text(value)
        if isinstance(value, dict):
            for sub_key in ("title", "name", "наименование", "наим", "значение", "value"):
                text = value.get(sub_key)
                if isinstance(text, str) and clean_text(text):
                    return clean_text(text)
        if isinstance(value, list) and value:
            return status_text_of(value[0])
        return ""

    def walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_text = str(key)
                full_path = f"{path}.{key_text}" if path else key_text
                if _STATUS_KEY_RE.search(key_text) and not info.status_text:
                    text = status_text_of(value)
                    if text and len(text) <= 120:
                        info.status_text = text
                if isinstance(value, (dict, list)):
                    walk(value, full_path)
                    continue
                if value in (None, ""):
                    continue
                text_value = clean_text(value) if isinstance(value, (str, int, float)) else ""
                if _PHONE_KEY_RE.search(key_text) and text_value:
                    merge_unique(info.phones, extract_phones(text_value))
                elif _EMAIL_KEY_RE.search(key_text) and text_value:
                    merge_unique(info.emails, extract_emails(text_value))
                elif _ADDRESS_KEY_RE.search(key_text) and len(text_value) >= 15:
                    merge_unique(info.addresses, [text_value])
                elif _DIRECTOR_KEY_RE.search(key_text) and text_value:
                    fio = extract_fio(text_value)
                    if fio:
                        merge_unique(info.directors, [fio])
                if _DATE_KEY_RE.search(key_text) and not _IGNORE_KEY_RE.search(full_path):
                    parsed = _clean_date_value(value)
                    if parsed is None:
                        continue
                    if _EXIT_KEY_RE.search(full_path):
                        if info.date_exit is None or parsed > info.date_exit:
                            info.date_exit = parsed
                    elif _JOIN_KEY_RE.search(full_path):
                        if info.date_join is None or parsed < info.date_join:
                            info.date_join = parsed
        elif isinstance(node, list):
            for item in node:
                walk(item, path)

    walk(record)
    return info


# --------------------------------------------------------------------------- #
#                                  HTTP-клиент                                 #
# --------------------------------------------------------------------------- #

class NostroyClient:
    """
    Клиент открытого реестра НОСТРОЙ. Ключей не требует.

    Официального лимита у реестра нет, но это общий публичный ресурс —
    частота запросов ограничивается вежливо (по умолчанию 1 запрос/с),
    а повторные запуски берут ответы из кэша состояния.
    """

    def __init__(self, settings: Settings, sample_path: Any = None) -> None:
        from .checko_client import RateLimiter

        self.settings = settings
        self._rate_limiter = RateLimiter(settings.nostroy_rps)
        self._local = threading.local()
        self._sample_path = sample_path
        self._sample_saved = False
        self._lock = threading.Lock()
        self._working_endpoint: str | None = None
        self._dead = False           # реестр недоступен — дальше не пытаемся

    @property
    def session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": self.settings.user_agent,
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json",
                    "Origin": NOSTROY_BASE,
                    "Referer": f"{NOSTROY_BASE}/",
                }
            )
            proxies = self.settings.proxies()
            if proxies:
                session.proxies.update(proxies)
            self._local.session = session
        return session

    def close(self) -> None:
        session = getattr(self._local, "session", None)
        if session is not None:
            session.close()
            self._local.session = None

    @property
    def is_dead(self) -> bool:
        return self._dead

    def _save_sample(self, response: requests.Response, endpoint: str) -> None:
        if self._sample_path is None:
            return
        with self._lock:
            if self._sample_saved:
                return
            self._sample_saved = True
        try:
            payload = {
                "запрос": {"endpoint": endpoint, "метод": "POST"},
                "ответ": {
                    "http_код": response.status_code,
                    "тип_содержимого": response.headers.get("Content-Type", ""),
                    "тело": response.text[:200000],
                },
            }
            self._sample_path.parent.mkdir(parents=True, exist_ok=True)
            self._sample_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info("Образец ответа реестра НОСТРОЙ сохранён: %s", self._sample_path)
        except (OSError, ValueError) as exc:
            logger.debug("Не удалось сохранить образец ответа реестра: %s", exc)

    def _bodies_for(self, inn: str) -> tuple[dict[str, Any], ...]:
        """Варианты тела запроса — по убыванию вероятности успеха."""
        return (
            {"filters": {"member_inn": inn}, "page": 1, "pageSize": 20},
            {"filters": {"inn": inn}, "page": 1, "pageSize": 20},
            {"searchString": inn, "page": 1, "pageSize": 20},
        )

    def lookup(self, inn: str) -> NostroyMemberInfo:
        """Запрашивает запись члена по ИНН. Никогда не выбрасывает исключений."""
        info = NostroyMemberInfo(inn=inn, fetched_at=utcnow_iso())
        inn = re.sub(r"\D", "", inn)
        if len(inn) not in (10, 12):
            info.error = "нет ИНН — реестр ищет только по ИНН"
            return info
        if self._dead:
            info.error = "реестр НОСТРОЙ недоступен (предыдущие запросы не прошли)"
            return info

        endpoints = (
            (self._working_endpoint,) if self._working_endpoint else _LIST_ENDPOINTS
        )
        failures = 0
        last_error = ""
        for endpoint in endpoints:
            for body in self._bodies_for(inn):
                self._rate_limiter.wait()
                try:
                    response = self.session.post(
                        f"{NOSTROY_BASE}{endpoint}",
                        json=body,
                        timeout=self.settings.timeout,
                    )
                except requests.exceptions.RequestException as exc:
                    last_error = f"сетевая ошибка: {exc}"
                    failures += 1
                    if failures >= 3:
                        break
                    time.sleep(min(2.0 * failures, 6.0) + random.uniform(0, 0.5))
                    continue

                self._save_sample(response, endpoint)
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code} от {endpoint}"
                    break        # другой вариант тела не поможет — меняем endpoint
                try:
                    payload = response.json()
                except ValueError:
                    last_error = "ответ реестра не является JSON"
                    break

                parsed = parse_member_payload(payload, inn)
                if parsed.found:
                    self._working_endpoint = endpoint
                    return parsed
                last_error = parsed.error
                # Запись не найдена, но запрос прошёл — пробуем другое тело.
            if failures >= 3:
                break

        if failures >= 3:
            self._dead = True
            logger.warning(
                "Реестр НОСТРОЙ недоступен (%s) — даты будут только из вашего файла",
                last_error,
            )
        info.error = last_error or "запись не найдена"
        return info
