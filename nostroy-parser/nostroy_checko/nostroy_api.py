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

#: Базовый адрес реестра НОСТРОЙ (строители).
NOSTROY_BASE = "https://reestr.nostroy.ru"

#: Базовый адрес реестра НОПРИЗ (проектировщики и изыскатели).
#: Многие компании состоят в СРО проектировщиков, и в реестре НОСТРОЙ их нет —
#: без второго источника у них навсегда оставались бы пустые даты.
NOPRIZ_BASE = "https://reestr.nopriz.ru"

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
#: Узел, описывающий саму СРО, а не компанию.
_SRO_KEY_RE = re.compile(r"(^|_)sro($|_)|сро|саморегул|self_regul", re.IGNORECASE)
#: Регистрационный номер СРО: СРО-С-410-16122014 (С — строители, П/И — проектировщики и изыскатели).
_SRO_NUMBER_RE = re.compile(r"СРО-[А-ЯЁ]-\d{3}-\d{6,8}", re.IGNORECASE)
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
    registry: str = ""               # какой реестр ответил: НОСТРОЙ или НОПРИЗ
    sro_name: str = ""               # наименование СРО, в которой состоит компания
    sro_number: str = ""             # регистрационный номер СРО (СРО-С-410-...)
    sro_inn: str = ""                # ИНН самой СРО — для однозначной сверки
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
            "registry": self.registry,
            "sro_name": self.sro_name,
            "sro_number": self.sro_number,
            "sro_inn": self.sro_inn,
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
            registry=data.get("registry", ""),
            sro_name=data.get("sro_name", ""),
            sro_number=data.get("sro_number", ""),
            sro_inn=data.get("sro_inn", ""),
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
    _extract_sro(record, info)
    return info


def _node_title(node: Any) -> str:
    """Наименование из объекта СРО — у реестра оно лежит под разными ключами."""
    if isinstance(node, str):
        return clean_text(node)
    if isinstance(node, dict):
        for key in ("full_description", "full_name", "title", "name", "наименование", "наим"):
            value = node.get(key)
            if isinstance(value, str) and clean_text(value):
                return clean_text(value)
    return ""


def _extract_sro(record: dict[str, Any], info: NostroyMemberInfo) -> None:
    """Достаёт из записи, В КАКОЙ СРО состоит компания.

    Реестр кладёт СРО отдельным узлом рядом с данными члена. Разбор ведётся
    по смыслу ключей, а не по фиксированной схеме: имена полей у НОСТРОЙ
    и НОПРИЗ различаются, и менялись со временем.
    """
    def visit(node: Any, inside_sro: bool = False) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_text = str(key)
                here = inside_sro or bool(_SRO_KEY_RE.search(key_text))

                if here and not info.sro_name:
                    title = _node_title(value)
                    # Наименование СРО длинное («Ассоциация …»); короткие
                    # строки — это статусы и идентификаторы, а не название.
                    if len(title) >= 10:
                        info.sro_name = title

                if isinstance(value, (str, int)):
                    text = clean_text(value)
                    match = _SRO_NUMBER_RE.search(text)
                    if match and not info.sro_number:
                        info.sro_number = match.group(0).upper()
                    if here and not info.sro_inn and _INN_KEY_RE.search(key_text):
                        digits = re.sub(r"\D", "", text)
                        if len(digits) == 10 and digits != info.inn:
                            info.sro_inn = digits

                if isinstance(value, (dict, list)):
                    visit(value, here)
        elif isinstance(node, list):
            for item in node:
                visit(item, inside_sro)

    visit(record)


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

    def __init__(
        self,
        settings: Settings,
        sample_path: Any = None,
        base_url: str = NOSTROY_BASE,
        title: str = "НОСТРОЙ",
    ) -> None:
        from .checko_client import RateLimiter

        self.settings = settings
        self.base_url = base_url
        self.title = title
        self._last_error = ""
        self._rate_limiter = RateLimiter(settings.nostroy_rps)
        self._local = threading.local()
        self._sample_path = sample_path
        self._sample_saved = False
        self._lock = threading.Lock()
        self._working_endpoint: str | None = None
        self._working_body: int | None = None    # индекс сработавшего варианта тела
        self._dead = False           # реестр недоступен — дальше не пытаемся
        self._failures = 0           # подряд идущие сетевые сбои (общие на все потоки)

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
                    "Origin": self.base_url,
                    "Referer": f"{self.base_url}/",
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
            logger.info("Образец ответа реестра %s сохранён: %s", self.title, self._sample_path)
        except (OSError, ValueError) as exc:
            logger.debug("Не удалось сохранить образец ответа реестра: %s", exc)

    def _bodies_for(self, value: str) -> tuple[dict[str, Any], ...]:
        """Варианты тела запроса — по убыванию вероятности успеха."""
        return (
            {"filters": {"member_inn": value}, "page": 1, "pageSize": 20},
            {"filters": {"inn": value}, "page": 1, "pageSize": 20},
            {"searchString": value, "page": 1, "pageSize": 20},
            {"filters": {"search": value}, "page": 1, "pageSize": 20},
        )

    def _query(self, value: str, inn: str, only_working: bool) -> NostroyMemberInfo | None:
        """
        Один заход поиска по значению ``value`` (ИНН, ОГРН или названию).

        :param only_working: использовать лишь уже известный рабочий формат
            запроса (быстрый путь). При ``False`` перебираются все варианты —
            так добираются компании, которых быстрый путь не нашёл.
        :return: найденную запись либо ``None``.
        """
        endpoints = (
            (self._working_endpoint,) if self._working_endpoint else _LIST_ENDPOINTS
        )
        bodies = list(enumerate(self._bodies_for(value)))
        if only_working and self._working_body is not None:
            bodies = [bodies[self._working_body]]

        for endpoint in endpoints:
            for body_index, body in bodies:
                if self._dead:
                    return None
                self._rate_limiter.wait()
                try:
                    response = self.session.post(
                        f"{self.base_url}{endpoint}",
                        json=body,
                        timeout=self.settings.timeout,
                    )
                except requests.exceptions.RequestException as exc:
                    self._last_error = f"сетевая ошибка: {exc}"
                    with self._lock:
                        self._failures += 1
                        if self._failures >= 5:
                            self._dead = True
                    if self._dead:
                        return None
                    time.sleep(1.0 + random.uniform(0, 0.5))
                    continue

                with self._lock:
                    self._failures = 0
                self._save_sample(response, endpoint)
                if response.status_code != 200:
                    self._last_error = f"HTTP {response.status_code} от {endpoint}"
                    break        # другой вариант тела не поможет — меняем endpoint
                try:
                    payload = response.json()
                except ValueError:
                    self._last_error = "ответ реестра не является JSON"
                    break

                parsed = parse_member_payload(payload, inn)
                if parsed.found:
                    with self._lock:
                        self._working_endpoint = endpoint
                        self._working_body = body_index
                    return parsed
                self._last_error = parsed.error
        return None

    def fetch_sro_members(
        self,
        sro_id: str,
        page_size: int = 100,
        max_pages: int = 200,
    ) -> dict[str, NostroyMemberInfo]:
        """
        Забирает СРАЗУ ВЕСЬ список членов одной СРО, страницами.

        Это на порядок быстрее поштучного поиска: полторы тысячи компаний
        приезжают за полтора десятка запросов вместо полутора тысяч. Именно так
        данные и лежат в реестре — список членов конкретной СРО.

        Возвращает ``{ИНН: сведения}``. Пустой словарь означает, что массовая
        загрузка не удалась (неизвестен формат фильтра, реестр недоступен) —
        вызывающий код в этом случае возвращается к поштучному поиску.
        """
        digits = re.sub(r"\D", "", sro_id or "")
        if not digits:
            return {}

        # Имя фильтра по СРО в открытом API не описано, поэтому пробуем
        # известные варианты и берём тот, который вернул записи.
        filter_variants: tuple[dict[str, Any], ...] = (
            {"sro_id": digits},
            {"sro": digits},
            {"sro_number": digits},
            {"sroId": digits},
            {"sro_registration_number": digits},
        )
        endpoints = (
            (self._working_endpoint,) if self._working_endpoint else _LIST_ENDPOINTS
        )

        for endpoint in endpoints:
            for filters in filter_variants:
                collected: dict[str, NostroyMemberInfo] = {}
                for page in range(1, max_pages + 1):
                    if self._dead:
                        return collected
                    body = {"filters": filters, "page": page, "pageSize": page_size}
                    self._rate_limiter.wait()
                    try:
                        response = self.session.post(
                            f"{self.base_url}{endpoint}",
                            json=body,
                            timeout=self.settings.timeout,
                        )
                    except requests.exceptions.RequestException as exc:
                        self._last_error = f"сетевая ошибка: {exc}"
                        break
                    self._save_sample(response, endpoint)
                    if response.status_code != 200:
                        self._last_error = f"HTTP {response.status_code}"
                        break
                    try:
                        payload = response.json()
                    except ValueError:
                        self._last_error = "ответ реестра не является JSON"
                        break

                    records: list[dict[str, Any]] = []
                    _collect_member_records(payload, records)
                    fresh = 0
                    for record in records:
                        inn = _record_inn(record)
                        if not inn or inn in collected:
                            continue
                        info = parse_member_payload(record, inn)
                        if info.found:
                            info.registry = self.title
                            collected[inn] = info
                            fresh += 1
                    if fresh == 0:
                        break          # страницы кончились либо фильтр не тот
                    logger.info(
                        "  %s: загружено записей списка — %d", self.title, len(collected)
                    )
                if len(collected) >= 10:
                    with self._lock:
                        self._working_endpoint = endpoint
                    return collected
        return {}

    def lookup(self, inn: str, ogrn: str = "", name: str = "") -> NostroyMemberInfo:
        """
        Ищет члена СРО по ИНН, а при неудаче — по ОГРН и по названию.

        Перебор запасных ключей нужен ради полноты: часть записей в реестре
        заполнена так, что поиск по ИНН их не находит, а по ОГРН или названию
        находит. Быстрый путь (известный формат запроса) пробуется первым,
        поэтому на подавляющем большинстве компаний по-прежнему один запрос.

        Никогда не выбрасывает исключений.
        """
        info = NostroyMemberInfo(inn=inn, fetched_at=utcnow_iso())
        inn = re.sub(r"\D", "", inn)
        if len(inn) not in (10, 12):
            info.error = "нет ИНН — реестр ищет только по реквизитам"
            return info
        if self._dead:
            info.error = f"реестр {self.title} недоступен"
            return info

        self._last_error = ""
        # 1) быстрый путь: известный формат запроса, поиск по ИНН
        found = self._query(inn, inn, only_working=True)
        # 2) полный перебор форматов по ИНН
        if found is None and not self._dead and self._working_body is not None:
            found = self._query(inn, inn, only_working=False)
        # 3) запасные ключи поиска — ОГРН и название
        if found is None and not self._dead:
            for fallback in (re.sub(r"\D", "", ogrn or ""), clean_text(name)):
                if not fallback or len(fallback) < 5:
                    continue
                found = self._query(fallback, inn, only_working=False)
                if found is not None:
                    break

        if found is not None:
            return found
        if self._dead:
            logger.warning(
                "Реестр %s недоступен (%s) — даты будут из других источников",
                self.title, self._last_error,
            )
        info.error = self._last_error or "запись не найдена"
        return info
