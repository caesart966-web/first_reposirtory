"""
Клиент официального API checko.ru (https://api.checko.ru/v2/).

Зачем он нужен помимо разбора HTML. Сайт checko.ru закрыт защитой от
автоматизации: обычный HTTP-клиент получает либо 403, либо страницу-заглушку,
поэтому разбор вёрстки — вариант «на удачу». Официальный API отдаёт те же
сведения структурированным JSON, не ломается при смене дизайна сайта и
как раз имеет бесплатный тариф со 100 запросами в сутки — ровно тот лимит,
под который построена вся логика работы «по дням».

Ключ выдаётся в личном кабинете checko.ru и передаётся ключом
``--checko-api-key`` или переменной окружения ``CHECKO_API_KEY``.

Разбор ответа намеренно устойчив к точным именам полей: сначала берём значения
по известным путям (``Контакты.Тел``, ``ЮрАдрес.АдресРФ``, ``Руковод[].ФИО``),
а затем проходим по всему JSON рекурсивно и добираем телефоны, почту и адреса
из любых других полей. Так клиент переживёт переименование полей в API.
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
from typing import Any

import requests

from .config import Settings
from .logging_setup import get_logger
from .models import (
    STATUS_ERROR,
    STATUS_FORBIDDEN,
    STATUS_NOT_FOUND,
    STATUS_OK,
    STATUS_RATE_LIMITED,
    CheckoContacts,
    utcnow_iso,
)
from .quota import DailyQuota
from .textutils import (
    clean_text,
    extract_emails,
    extract_phones,
    merge_unique,
    normalize_phone,
)

logger = get_logger("checko-api")

#: Пометка источника данных в сохранённом результате.
SOURCE_API = "api"

#: Базовый адрес API.
CHECKO_API_BASE = "https://api.checko.ru/v2"

#: Эндпоинт по типу лица: 10 цифр ИНН — организация, 12 — ИП.
ENDPOINT_COMPANY = "company"
ENDPOINT_ENTREPRENEUR = "entrepreneur"

# --- Классификация ключей JSON (регистр и «ё» не важны) --------------------- #
_KEY_PHONE = re.compile(r"^(тел|телефон|phone|тел\w*)$", re.IGNORECASE)
_KEY_EMAIL = re.compile(r"^(емэйл|емейл|email|e-?mail|почта)$", re.IGNORECASE)
_KEY_ADDRESS = re.compile(r"(адрес|address)", re.IGNORECASE)
_KEY_SITE = re.compile(r"(вебсайт|сайт|website|site|url)", re.IGNORECASE)
_KEY_NAME_FULL = re.compile(r"^(наимполн|наимполнюл|наименованиеполное|наимюл)$", re.IGNORECASE)
_KEY_NAME_SHORT = re.compile(r"^(наимсокр|наимсокрюл|наименование|наим|name)$", re.IGNORECASE)
_KEY_DIRECTOR = re.compile(r"^(руковод|руководитель|директор|управляющ\w*)$", re.IGNORECASE)
_KEY_FIO = re.compile(r"^(фио|fio|name)$", re.IGNORECASE)
_KEY_POSITION = re.compile(r"^(наимдолжн|должность|должн)$", re.IGNORECASE)

#: Сообщения API, по которым определяем особые состояния.
_MSG_LIMIT = ("лимит", "превыш", "limit", "quota", "исчерпан")
_MSG_NOT_FOUND = ("не найден", "не найдено", "отсутств", "not found", "нет данных")
_MSG_BAD_KEY = ("ключ", "key", "авториз", "unauthorized", "доступ", "тариф", "подписк")


def _walk(node: Any, callback: Any, path: str = "") -> None:
    """Рекурсивно обходит JSON, вызывая ``callback(ключ, значение, путь)``."""
    if isinstance(node, dict):
        for key, value in node.items():
            callback(str(key), value, f"{path}.{key}" if path else str(key))
            _walk(value, callback, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _walk(item, callback, f"{path}[{index}]")


def _as_text_list(value: Any) -> list[str]:
    """Приводит значение поля к списку строк (API отдаёт то строку, то массив)."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (int, float)):
        return [str(value)]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_as_text_list(item))
        return result
    if isinstance(value, dict):
        # Телефон может приходить объектом {"Значение": "...", "Тип": "..."}.
        for key in ("Значение", "Знач", "value", "АдресРФ", "Адрес", "Тел", "Емэйл"):
            if key in value:
                return _as_text_list(value[key])
    return []


def parse_api_payload(data: Any, expected_inn: str = "") -> CheckoContacts:
    """
    Превращает ``data`` из ответа API в :class:`CheckoContacts`.

    Функция не делает сетевых вызовов — её удобно проверять на сохранённом
    JSON и она же используется в автотестах.
    """
    result = CheckoContacts(status=STATUS_OK, fetched_at=utcnow_iso(), source=SOURCE_API)
    if not isinstance(data, (dict, list)):
        result.status = STATUS_NOT_FOUND
        result.error = "в ответе API нет данных о компании"
        return result

    # Если API вернул список совпадений — берём первое.
    if isinstance(data, list):
        data = data[0] if data else {}

    raw_addresses: list[str] = []
    directors: list[str] = []
    # Названия собираем с приоритетом: полное > сокращённое > произвольное «Наим».
    # Иначе вложенное поле вроде ``Регион.Наим`` могло бы стать названием компании.
    name_candidates: dict[int, str] = {}

    def visit(key: str, value: Any, path: str) -> None:
        """Классифицирует одно поле JSON."""
        lowered = key.lower().replace("ё", "е")
        lowered_path = path.lower().replace("ё", "е")

        if _KEY_PHONE.match(lowered):
            for item in _as_text_list(value):
                merge_unique(result.phones, extract_phones(item) or [normalize_phone(item)])
        elif _KEY_EMAIL.match(lowered):
            for item in _as_text_list(value):
                merge_unique(result.emails, extract_emails(item))
        elif _KEY_SITE.search(lowered):
            for item in _as_text_list(value):
                text = clean_text(item)
                if text and "." in text:
                    merge_unique(result.websites, [text])
        elif _KEY_ADDRESS.search(lowered):
            for item in _as_text_list(value):
                text = clean_text(item)
                # Отсекаем куски адреса (регион, индекс) — нужен полный адрес.
                if len(text) >= 15:
                    merge_unique(raw_addresses, [text])
        elif _KEY_NAME_FULL.match(lowered) and isinstance(value, str):
            name_candidates.setdefault(3, clean_text(value))
        elif _KEY_NAME_SHORT.match(lowered) and isinstance(value, str):
            # Обобщённое «Наим» принимаем только на верхнем уровне ответа:
            # глубже так называются регион, статус, вид деятельности и прочее.
            priority = 2 if lowered.startswith("наимсокр") else (1 if "." not in path else 0)
            if priority:
                name_candidates.setdefault(priority, clean_text(value))
        elif lowered == "инн" and not result.inn:
            digits = re.sub(r"\D", "", str(value))
            if len(digits) in (10, 12):
                result.inn = digits
        elif lowered in ("огрн", "огрнип") and not result.ogrn:
            digits = re.sub(r"\D", "", str(value))
            if len(digits) in (13, 15):
                result.ogrn = digits
        elif _KEY_DIRECTOR.match(lowered):
            # Руководитель может быть объектом, списком объектов или строкой.
            items = value if isinstance(value, list) else [value]
            for item in items:
                if isinstance(item, dict):
                    fio = ""
                    position = ""
                    for sub_key, sub_value in item.items():
                        if _KEY_FIO.match(str(sub_key).lower()) and isinstance(sub_value, str):
                            fio = clean_text(sub_value)
                        elif _KEY_POSITION.match(str(sub_key).lower()) and isinstance(sub_value, str):
                            position = clean_text(sub_value)
                    if fio:
                        # В отчёт нужно только ФИО — должность не сохраняем.
                        merge_unique(directors, [fio])
                    elif position and not fio:
                        merge_unique(directors, [position])
                elif isinstance(item, str) and clean_text(item):
                    merge_unique(directors, [clean_text(item)])
        # ФИО индивидуального предпринимателя — это и есть название.
        elif _KEY_FIO.match(lowered) and "руковод" not in lowered_path:
            if isinstance(value, str) and clean_text(value):
                name_candidates.setdefault(2, clean_text(value))

    visit("__root__", data, "")
    _walk(data, visit)

    if name_candidates:
        result.name = name_candidates[max(name_candidates)]

    # Самый подробный адрес считаем основным.
    if raw_addresses:
        result.addresses = [max(raw_addresses, key=len)]
        merge_unique(result.addresses, raw_addresses)
    result.directors = directors

    # Запасной проход: телефоны и почта могли лежать в полях с непредвиденным
    # именем — ищем их по всему тексту ответа.
    if not result.phones or not result.emails:
        blob = json.dumps(data, ensure_ascii=False)
        if not result.emails:
            merge_unique(result.emails, extract_emails(blob, limit=5))
        if not result.phones:
            merge_unique(result.phones, extract_phones(blob, limit=5))

    if expected_inn:
        result.inn_matched = (result.inn == expected_inn) if result.inn else None

    if not (result.name or result.has_contacts):
        result.status = STATUS_NOT_FOUND
        result.error = "API вернул пустую карточку"
    return result


class CheckoApiClient:
    """
    Клиент официального API checko.ru.

    Интерфейс совпадает с :class:`~nostroy_checko.checko_client.CheckoClient`
    (``lookup`` и ``close``), поэтому конвейер использует их взаимозаменяемо.
    Одна компания — ровно один HTTP-запрос и одна единица суточной квоты.
    """

    def __init__(
        self,
        settings: Settings,
        quota: DailyQuota,
        sample_path: Any = None,
    ) -> None:
        from .checko_client import RateLimiter   # общий ограничитель частоты

        self.settings = settings
        self.quota = quota
        self.api_key = (settings.checko_api_key or "").strip()
        self._rate_limiter = RateLimiter(settings.rps)
        self._local = threading.local()
        self._no_inn_count = 0
        self._lock = threading.Lock()
        # Куда сохранить первый ответ API целиком. Нужно для разбора полётов:
        # по нему видно точные имена полей, не тратя лишние запросы квоты.
        self._sample_path = sample_path
        self._sample_saved = False
        # Каким методом сервер согласился отвечать. Определяется один раз и
        # дальше переиспользуется, чтобы не пробовать оба на каждой компании.
        self._method: str | None = None

    def _save_sample(self, response: requests.Response, method: str) -> None:
        """
        Кладёт первый ответ API в файл (ключ вырезается).

        Формат ответа сервиса может измениться или отличаться от ожидаемого —
        сохранённый образец позволяет это увидеть и поправить разбор, не тратя
        запросы из суточной квоты на эксперименты.
        """
        if self._sample_path is None:
            return
        with self._lock:
            if self._sample_saved:
                return
            self._sample_saved = True
        try:
            body = response.text
            if self.api_key:
                body = body.replace(self.api_key, "***КЛЮЧ-СКРЫТ***")
            url = response.url.replace(self.api_key, "***КЛЮЧ-СКРЫТ***") if self.api_key else response.url
            payload = {
                "запрос": {"метод": method, "url": url},
                "ответ": {
                    "http_код": response.status_code,
                    "тип_содержимого": response.headers.get("Content-Type", ""),
                    "тело": body[:200000],
                },
            }
            self._sample_path.parent.mkdir(parents=True, exist_ok=True)
            self._sample_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info("Образец ответа API сохранён: %s", self._sample_path)
        except (OSError, ValueError) as exc:
            logger.debug("Не удалось сохранить образец ответа API: %s", exc)

    def _request(self, url: str, params: dict[str, str]) -> requests.Response:
        """
        Выполняет запрос к API, сам определяя нужный HTTP-метод.

        Документация сервиса описывает и GET с параметрами в строке запроса,
        и POST с телом. Чтобы не зависеть от догадок, первый раз пробуем GET,
        и если сервер отвечает «метод не поддерживается» или «нет параметров» —
        повторяем POST'ом. Найденный метод запоминается для всех следующих
        запросов, лишних обращений не будет.
        """
        method = self._method
        if method in (None, "GET"):
            response = self.session.get(url, params=params, timeout=self.settings.timeout)
            # 405 — метод не тот; 400/415 — сервер не понял параметры в строке.
            if method is None and response.status_code in (400, 404, 405, 415):
                logger.info(
                    "API ответил %s на GET — повторяю запрос методом POST",
                    response.status_code,
                )
                post_response = self.session.post(
                    url, json=params, timeout=self.settings.timeout
                )
                if post_response.status_code == 200:
                    self._method = "POST"
                    return post_response
                # POST не помог — значит дело не в методе, возвращаем первый ответ.
                self._method = "GET"
                return response
            if method is None and response.status_code == 200:
                self._method = "GET"
            return response
        return self.session.post(url, json=params, timeout=self.settings.timeout)

    # ------------------------------ сессия --------------------------------- #

    @property
    def session(self) -> requests.Session:
        """Сессия requests, своя для каждого потока."""
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update(
                {
                    "User-Agent": self.settings.user_agent,
                    "Accept": "application/json",
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

    # ------------------------------ запрос --------------------------------- #

    def _sleep_backoff(self, attempt: int) -> None:
        delay = min(2.0 ** attempt, 30.0) + random.uniform(0.0, 0.75)
        time.sleep(delay)

    def lookup(self, query: str, expected_inn: str = "") -> CheckoContacts:
        """
        Запрашивает карточку компании по ИНН.

        API ищет строго по реквизитам (ИНН/ОГРН), поиска по названию в нём нет,
        поэтому записи без ИНН пропускаются с понятным сообщением — квота на них
        не тратится.
        """
        inn = re.sub(r"\D", "", expected_inn or query)
        result = CheckoContacts(query=query, fetched_at=utcnow_iso(), attempts=1,
                                source=SOURCE_API)

        if len(inn) not in (10, 12):
            with self._lock:
                self._no_inn_count += 1
            result.status = STATUS_NOT_FOUND
            result.error = "у записи нет ИНН, а API checko.ru ищет только по ИНН/ОГРН"
            return result

        endpoint = ENDPOINT_COMPANY if len(inn) == 10 else ENDPOINT_ENTREPRENEUR
        url = f"{CHECKO_API_BASE}/{endpoint}"
        params = {"key": self.api_key, "inn": inn}

        for attempt in range(self.settings.max_retries + 1):
            self._rate_limiter.wait()
            try:
                response = self._request(url, params)
            except requests.exceptions.Timeout as exc:
                result.error = f"таймаут: {exc}"
                if attempt < self.settings.max_retries:
                    self._sleep_backoff(attempt)
                    continue
                result.status = STATUS_ERROR
                return result
            except requests.exceptions.RequestException as exc:
                result.error = f"ошибка запроса: {exc}"
                if attempt < self.settings.max_retries:
                    self._sleep_backoff(attempt)
                    continue
                result.status = STATUS_ERROR
                return result

            result.http_status = response.status_code
            result.url = f"{url}?inn={inn}"
            self._save_sample(response, self._method or "GET")

            if response.status_code in (401, 403):
                self.quota.mark_exhausted(
                    f"API вернул {response.status_code}: проверьте ключ и тариф checko.ru"
                )
                result.status = STATUS_FORBIDDEN
                result.error = f"HTTP {response.status_code}: ключ отклонён"
                return result
            if response.status_code == 429:
                self.quota.mark_exhausted("HTTP 429: исчерпан суточный лимит API")
                result.status = STATUS_RATE_LIMITED
                result.error = "HTTP 429: превышен лимит запросов"
                return result
            if response.status_code == 404:
                result.status = STATUS_NOT_FOUND
                result.error = "HTTP 404: компания не найдена"
                return result
            if 500 <= response.status_code < 600:
                result.error = f"HTTP {response.status_code}: ошибка сервера"
                if attempt < self.settings.max_retries:
                    self._sleep_backoff(attempt)
                    continue
                result.status = STATUS_ERROR
                return result
            if response.status_code != 200:
                result.status = STATUS_ERROR
                result.error = f"HTTP {response.status_code}"
                return result

            try:
                payload = response.json()
            except ValueError as exc:
                result.status = STATUS_ERROR
                result.error = f"ответ API не является JSON: {exc}"
                return result

            return self._interpret(payload, query, inn, result)

        result.status = STATUS_ERROR
        return result

    def _interpret(
        self,
        payload: Any,
        query: str,
        inn: str,
        base: CheckoContacts,
    ) -> CheckoContacts:
        """Разбирает успешный ответ API, учитывая служебный блок ``meta``."""
        meta = payload.get("meta") if isinstance(payload, dict) else None
        message = ""
        status_field = ""
        if isinstance(meta, dict):
            message = str(meta.get("message", "") or "")
            status_field = str(meta.get("status", "") or "").lower()

        lowered = message.lower().replace("ё", "е")
        if any(marker in lowered for marker in _MSG_LIMIT):
            self.quota.mark_exhausted(f"API сообщает: {message}")
            base.status = STATUS_RATE_LIMITED
            base.error = message
            return base
        if any(marker in lowered for marker in _MSG_BAD_KEY):
            self.quota.mark_exhausted(f"API сообщает: {message}")
            base.status = STATUS_FORBIDDEN
            base.error = message
            return base
        if any(marker in lowered for marker in _MSG_NOT_FOUND):
            base.status = STATUS_NOT_FOUND
            base.error = message
            return base
        if status_field and status_field not in ("ok", "200", "success"):
            base.status = STATUS_ERROR
            base.error = message or f"API вернул статус {status_field!r}"
            return base

        data = payload.get("data") if isinstance(payload, dict) else payload
        parsed = parse_api_payload(data, expected_inn=inn)
        parsed.query = query
        parsed.url = base.url
        parsed.http_status = base.http_status
        parsed.attempts = 1
        if parsed.status == STATUS_NOT_FOUND and message:
            parsed.error = message
        return parsed

    def report_skipped(self) -> None:
        """Пишет в лог, сколько записей пропущено из-за отсутствия ИНН."""
        with self._lock:
            count = self._no_inn_count
        if count:
            logger.warning(
                "Пропущено записей без ИНН: %d — API checko.ru ищет только по ИНН/ОГРН. "
                "Такие компании остались с контактами только из реестра НОСТРОЙ.",
                count,
            )
