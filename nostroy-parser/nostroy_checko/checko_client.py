"""
Клиент checko.ru: получение и разбор карточки компании.

Учитываются все особенности бесплатного доступа:

* строгий суточный лимит запросов (см. :mod:`nostroy_checko.quota`);
* ответы 429 (лимит исчерпан), 403 (блокировка/капча), 404 (не найдено);
* временные сетевые сбои и 5xx — повторяем с экспоненциальной задержкой;
* общий ограничитель частоты запросов, чтобы не «долбить» сервис
  даже при работе в несколько потоков.

Разбор страницы намеренно многослойный: сначала самые надёжные источники
(ссылки ``tel:``/``mailto:``, микроразметка JSON-LD), затем разбор пар
«подпись — значение», и лишь в конце — поиск по регулярным выражениям
во всём тексте. Данные из разных слоёв объединяются без дублей.
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
from html import unescape
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import requests

from .config import (
    CHECKO_BASE_URL,
    CHECKO_OWN_EMAIL_DOMAINS,
    CHECKO_OWN_EMAILS,
    CHECKO_OWN_PHONES,
    CHECKO_SEARCH_PATH,
    Settings,
)
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
    extract_fio,
    extract_phones,
    merge_unique,
    normalize_phone,
)

logger = get_logger("checko")

#: Пометка источника данных в сохранённом результате.
SOURCE_HTML = "html"

# --------------------------------------------------------------------------- #
#                          Маркеры состояний страницы                          #
# --------------------------------------------------------------------------- #

#: Признаки того, что бесплатный лимит запросов исчерпан.
_LIMIT_MARKERS: tuple[str, ...] = (
    "лимит запросов",
    "превышен лимит",
    "исчерпан лимит",
    "лимит бесплатных",
    "достигнут лимит",
    "превышено количество запросов",
    "too many requests",
)

#: Признаки блокировки / проверки «я не робот».
_BLOCK_MARKERS: tuple[str, ...] = (
    "подтвердите, что вы не робот",
    "проверка браузера",
    "captcha",
    "cf-browser-verification",
    "access denied",
    "доступ ограничен",
)

#: Признаки того, что поиск ничего не нашёл.
_NOT_FOUND_MARKERS: tuple[str, ...] = (
    "ничего не найдено",
    "не найдено ни одной",
    "по вашему запросу ничего",
    "результатов не найдено",
    "нет результатов",
)

#: Ссылки на карточки организаций и ИП.
_CARD_HREF_RE = re.compile(r"^/(company|ip|fl)/", re.IGNORECASE)
_CARD_URL_RE = re.compile(r"/(company|ip|fl)/", re.IGNORECASE)


# --------------------------------------------------------------------------- #
#                            Ограничитель частоты                              #
# --------------------------------------------------------------------------- #

class RateLimiter:
    """
    Общий на все потоки ограничитель частоты запросов.

    Гарантирует минимальный интервал между обращениями к сайту независимо
    от того, сколько рабочих потоков запущено.
    """

    def __init__(self, requests_per_second: float) -> None:
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        """Блокирует поток до момента, когда можно делать следующий запрос."""
        if self._min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            wait_for = max(0.0, self._next_allowed - now)
            self._next_allowed = max(now, self._next_allowed) + self._min_interval
        if wait_for > 0:
            time.sleep(wait_for)


# --------------------------------------------------------------------------- #
#                             Разбор HTML-страницы                             #
# --------------------------------------------------------------------------- #

def _make_soup(html: str) -> Any:
    """Создаёт BeautifulSoup с самым быстрым доступным парсером."""
    from bs4 import BeautifulSoup

    for parser in ("lxml", "html.parser"):
        try:
            return BeautifulSoup(html, parser)
        except Exception:  # noqa: BLE001 — lxml может быть не установлен
            continue
    return BeautifulSoup(html, "html.parser")


def _visible_text(soup: Any) -> str:
    """Текст страницы без скриптов и стилей (для поиска по регулярным выражениям)."""
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ", strip=True).split())


def _is_own_email(email: str) -> bool:
    """Отсеивает контакты самого сервиса checko.ru."""
    email = email.lower().strip()
    if email in CHECKO_OWN_EMAILS:
        return True
    domain = email.rsplit("@", 1)[-1]
    return domain in CHECKO_OWN_EMAIL_DOMAINS


def _is_own_phone(phone: str) -> bool:
    return normalize_phone(phone) in CHECKO_OWN_PHONES


def _extract_from_links(soup: Any) -> tuple[list[str], list[str], list[str]]:
    """
    Достаёт контакты из ссылок ``tel:``, ``mailto:`` и внешних сайтов.

    Самый надёжный источник: разметка ссылок не зависит от вёрстки текста.
    """
    phones: list[str] = []
    emails: list[str] = []
    websites: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        lowered = href.lower()
        if lowered.startswith("tel:"):
            phone = normalize_phone(unescape(href[4:]))
            if phone and not _is_own_phone(phone):
                merge_unique(phones, [phone])
        elif lowered.startswith("mailto:"):
            email = unescape(href[7:]).split("?", 1)[0].strip().lower()
            if email and "@" in email and not _is_own_email(email):
                merge_unique(emails, [email])
        elif lowered.startswith("http"):
            host = urlparse(lowered).netloc
            # Внешние сайты — вероятный сайт компании; свои и соцсети пропускаем.
            if host and not any(
                marker in host
                for marker in (
                    "checko", "yandex", "google", "vk.com", "facebook", "instagram",
                    "twitter", "t.me", "telegram", "youtube", "ok.ru", "apple.com",
                    "gosuslugi", "nalog.ru", "rusprofile", "zachestnyibiznes",
                )
            ):
                merge_unique(websites, [href])
    return phones, emails, websites


def _extract_from_json_ld(soup: Any) -> dict[str, Any]:
    """
    Разбирает микроразметку ``application/ld+json``.

    checko.ru отдаёт в ней название, ИНН/ОГРН, адрес, телефон и e-mail
    в машиночитаемом виде — это самый точный источник.
    """
    result: dict[str, Any] = {}

    def absorb(node: Any) -> None:
        """Рекурсивно вытаскивает интересные поля из произвольного JSON."""
        if isinstance(node, list):
            for item in node:
                absorb(item)
            return
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            lowered = key.lower()
            if lowered in ("telephone", "phone") and value:
                result.setdefault("phones", [])
                merge_unique(result["phones"], extract_phones(str(value)) or [str(value)])
            elif lowered == "email" and value:
                result.setdefault("emails", [])
                merge_unique(result["emails"], extract_emails(str(value)))
            elif lowered in ("name", "legalname") and value and "name" not in result:
                result["name"] = clean_text(str(value))
            elif lowered == "taxid" and value:
                result["inn"] = re.sub(r"\D", "", str(value))
            elif lowered in ("vatid", "leicode", "duns") and value and "ogrn" not in result:
                digits = re.sub(r"\D", "", str(value))
                if len(digits) in (13, 15):
                    result["ogrn"] = digits
            elif lowered == "address":
                if isinstance(value, str):
                    result.setdefault("addresses", [])
                    merge_unique(result["addresses"], [clean_text(value)])
                elif isinstance(value, dict):
                    parts = [
                        clean_text(str(value.get(field, "")))
                        for field in (
                            "postalCode", "addressCountry", "addressRegion",
                            "addressLocality", "streetAddress",
                        )
                    ]
                    joined = ", ".join(part for part in parts if part)
                    if joined:
                        result.setdefault("addresses", [])
                        merge_unique(result["addresses"], [joined])
                    absorb(value)
            elif lowered in ("employee", "founder", "member", "director") and value:
                names: list[str] = []
                items = value if isinstance(value, list) else [value]
                for item in items:
                    if isinstance(item, dict):
                        candidate = clean_text(str(item.get("name", "")))
                        if candidate:
                            names.append(candidate)
                    elif isinstance(item, str):
                        names.append(clean_text(item))
                if names:
                    result.setdefault("directors", [])
                    merge_unique(result["directors"], names)
            elif lowered in ("url", "sameas") and isinstance(value, str) and value.startswith("http"):
                if "checko" not in value:
                    result.setdefault("websites", [])
                    merge_unique(result["websites"], [value])
            elif isinstance(value, (dict, list)):
                absorb(value)

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            absorb(json.loads(raw))
        except (json.JSONDecodeError, TypeError, ValueError):
            # Некоторые сайты кладут в ld+json невалидный JSON — не беда.
            continue
    return result


#: Подписи полей на карточке компании -> внутреннее имя поля.
_LABEL_MAP: tuple[tuple[str, str], ...] = (
    (r"^телефон", "phones"),
    (r"^контактный телефон", "phones"),
    (r"^факс", "phones"),
    (r"^(эл(ектронная)?\.?\s*почта|e-?mail|почта)$", "emails"),
    (r"^(юридический\s+)?адрес", "addresses"),
    (r"^место\s*нахождени", "addresses"),
    (r"^(руководитель|генеральный директор|директор|president|президент)", "directors"),
    (r"^(управляющ|единоличный исполнительный орган)", "directors"),
    (r"^(сайт|веб-?сайт|website)", "websites"),
    (r"^инн$", "inn"),
    (r"^огрн(ип)?$", "ogrn"),
)

_LABEL_PATTERNS = tuple((re.compile(pattern, re.IGNORECASE), field) for pattern, field in _LABEL_MAP)


def _value_next_to(node: Any) -> str:
    """
    Находит значение, стоящее рядом с подписью.

    Перебираются типичные варианты вёрстки: ``<dt>/<dd>``, ячейки таблицы,
    соседний блок, родитель с подписью внутри.
    """
    element = node.parent if hasattr(node, "parent") else None
    for _ in range(3):
        if element is None:
            break
        name = getattr(element, "name", "") or ""
        # Вариант 1: соседний элемент того же уровня.
        sibling = element.find_next_sibling()
        if sibling is not None:
            text = clean_text(sibling.get_text(" ", strip=True))
            if text:
                return text
        # Вариант 2: <dt> -> <dd>, <th> -> <td>.
        if name in ("dt", "th", "td"):
            following = element.find_next(["dd", "td"])
            if following is not None:
                text = clean_text(following.get_text(" ", strip=True))
                if text:
                    return text
        # Вариант 3: подпись и значение в одном контейнере.
        parent_text = clean_text(element.get_text(" ", strip=True))
        label_text = clean_text(str(node))
        if parent_text and label_text and parent_text != label_text:
            remainder = parent_text.replace(label_text, "", 1).strip(" :–—-")
            if remainder:
                return remainder
        element = element.parent
    return ""


def _extract_by_labels(soup: Any) -> dict[str, list[str]]:
    """Собирает значения по подписям полей на карточке."""
    collected: dict[str, list[str]] = {}
    for text_node in soup.find_all(string=True):
        label = clean_text(str(text_node)).strip(" : ")
        if not label or len(label) > 60:
            continue
        for pattern, field in _LABEL_PATTERNS:
            if not pattern.match(label):
                continue
            value = _value_next_to(text_node)
            if not value or len(value) > 600:
                continue
            collected.setdefault(field, [])
            merge_unique(collected[field], [value])
            break
    return collected


def _detect_page_state(text: str) -> str | None:
    """
    Определяет особое состояние страницы: лимит, блокировка, «не найдено».

    :return: ``STATUS_RATE_LIMITED`` / ``STATUS_FORBIDDEN`` / ``STATUS_NOT_FOUND``
             либо ``None``, если страница обычная.
    """
    lowered = text.lower()
    if any(marker in lowered for marker in _LIMIT_MARKERS):
        return STATUS_RATE_LIMITED
    if any(marker in lowered for marker in _BLOCK_MARKERS):
        return STATUS_FORBIDDEN
    if any(marker in lowered for marker in _NOT_FOUND_MARKERS):
        return STATUS_NOT_FOUND
    return None


def parse_company_page(html: str, url: str, expected_inn: str = "") -> CheckoContacts:
    """
    Разбирает HTML карточки компании на checko.ru.

    :param html:         исходный HTML страницы;
    :param url:          адрес страницы (попадает в отчёт);
    :param expected_inn: ИНН, который мы искали — для проверки, что открылась
                         карточка нужной компании.
    """
    result = CheckoContacts(url=url, status=STATUS_OK, fetched_at=utcnow_iso(), source=SOURCE_HTML)
    soup = _make_soup(html)

    # --- заголовок карточки ------------------------------------------------ #
    heading = soup.find("h1")
    if heading is not None:
        result.name = clean_text(heading.get_text(" ", strip=True))

    text = _visible_text(soup)

    # Особое состояние страницы (лимит/блокировка/«не найдено») определяем
    # заранее, но решение принимаем в конце: карточка реальной компании важнее
    # любых баннеров, поэтому сначала пытаемся извлечь данные.
    state = _detect_page_state(text)

    # --- слой 1: ссылки tel:/mailto: --------------------------------------- #
    phones, emails, websites = _extract_from_links(soup)
    merge_unique(result.phones, phones)
    merge_unique(result.emails, emails)
    merge_unique(result.websites, websites)

    # --- слой 2: микроразметка JSON-LD ------------------------------------- #
    json_ld = _extract_from_json_ld(soup)
    merge_unique(result.phones, [normalize_phone(item) for item in json_ld.get("phones", [])])
    merge_unique(result.emails, [item for item in json_ld.get("emails", []) if not _is_own_email(item)])
    merge_unique(result.addresses, json_ld.get("addresses", []))
    merge_unique(result.directors, json_ld.get("directors", []))
    merge_unique(result.websites, json_ld.get("websites", []))
    if not result.name and json_ld.get("name"):
        result.name = json_ld["name"]
    if json_ld.get("inn"):
        result.inn = json_ld["inn"]
    if json_ld.get("ogrn"):
        result.ogrn = json_ld["ogrn"]

    # --- слой 3: пары «подпись — значение» --------------------------------- #
    by_label = _extract_by_labels(soup)
    for value in by_label.get("phones", []):
        merge_unique(result.phones, [item for item in extract_phones(value) if not _is_own_phone(item)])
    for value in by_label.get("emails", []):
        merge_unique(result.emails, [item for item in extract_emails(value) if not _is_own_email(item)])
    for value in by_label.get("addresses", []):
        if len(value) >= 10:
            merge_unique(result.addresses, [value])
    for value in by_label.get("directors", []):
        merge_unique(result.directors, [value])
    for value in by_label.get("websites", []):
        if "." in value:
            merge_unique(result.websites, [value])
    if not result.inn and by_label.get("inn"):
        digits = re.sub(r"\D", "", by_label["inn"][0])
        if len(digits) in (10, 12):
            result.inn = digits
    if not result.ogrn and by_label.get("ogrn"):
        digits = re.sub(r"\D", "", by_label["ogrn"][0])
        if len(digits) in (13, 15):
            result.ogrn = digits

    # --- слой 4: сплошной поиск по тексту ---------------------------------- #
    if not result.inn:
        match = re.search(r"ИНН[:\s]*(\d{10}|\d{12})(?!\d)", text)
        if match:
            result.inn = match.group(1)
    if not result.ogrn:
        match = re.search(r"ОГРН(?:ИП)?[:\s]*(\d{13}|\d{15})(?!\d)", text)
        if match:
            result.ogrn = match.group(1)
    if not result.phones:
        merge_unique(
            result.phones,
            [item for item in extract_phones(text, limit=5) if not _is_own_phone(item)],
        )
    if not result.emails:
        merge_unique(
            result.emails,
            [item for item in extract_emails(text, limit=5) if not _is_own_email(item)],
        )
    if not result.directors:
        match = re.search(
            r"(?:Руководител[ья]|Генеральный директор|Директор|Президент|Управляющий)"
            r"[^А-ЯЁ]{0,40}([А-ЯЁ][а-яё\-]+\s+[А-ЯЁ][а-яё\-]+(?:\s+[А-ЯЁ][а-яё\-]+)?)",
            text,
        )
        if match:
            result.directors.append(match.group(1).strip())
    if not result.addresses:
        match = re.search(r"(\d{6},[^;|]{10,200})", text)
        if match:
            result.addresses.append(clean_text(match.group(1)))

    # --- проверка, что открылась нужная компания --------------------------- #
    if expected_inn:
        if result.inn:
            result.inn_matched = result.inn == expected_inn
        else:
            result.inn_matched = expected_inn in text.replace(" ", "")
        if result.inn_matched is False:
            logger.warning(
                "ИНН на странице (%s) не совпал с запрошенным (%s): %s",
                result.inn or "—", expected_inn, url,
            )

    # Чистим список руководителей: убираем дубли и заведомый мусор.
    cleaned_directors: list[str] = []
    for value in result.directors:
        value = clean_text(value).strip(" :-—")
        # Значение должно содержать ФИО либо хотя бы выглядеть как имя человека.
        if value and (extract_fio(value) or len(value.split()) >= 2) and len(value) <= 200:
            merge_unique(cleaned_directors, [value])
    result.directors = cleaned_directors

    # --- итоговый статус --------------------------------------------------- #
    # «Полезными» считаем ИНН и контакты: если они есть, перед нами карточка
    # компании, а совпавший маркер лимита — просто баннер на странице.
    has_useful_data = bool(result.inn or result.has_contacts)
    if state in (STATUS_RATE_LIMITED, STATUS_FORBIDDEN) and not has_useful_data:
        result.status = state
        result.name = ""          # это не название компании, а текст баннера
        return result
    if not (result.name or has_useful_data):
        # Страница получена, но полезного в ней нет — считаем «не найдено».
        result.status = state or STATUS_NOT_FOUND
    return result


def find_card_link(html: str, base_url: str) -> str:
    """
    Находит на странице результатов поиска ссылку на карточку компании.

    Возвращает абсолютный URL или пустую строку.
    """
    soup = _make_soup(html)
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if _CARD_HREF_RE.match(href) or _CARD_URL_RE.search(href):
            return urljoin(base_url, href)
    return ""


# --------------------------------------------------------------------------- #
#                                  HTTP-клиент                                 #
# --------------------------------------------------------------------------- #

class CheckoClient:
    """
    Потокобезопасный клиент checko.ru.

    Каждый рабочий поток получает собственную ``requests.Session``
    (сессии requests не рассчитаны на совместное использование потоками),
    но квота и ограничитель частоты — общие.
    """

    #: Сколько подряд ответов 403 считаем блокировкой и прекращаем работу.
    FORBIDDEN_TOLERANCE = 3

    def __init__(self, settings: Settings, quota: DailyQuota) -> None:
        self.settings = settings
        self.quota = quota
        self._rate_limiter = RateLimiter(settings.rps)
        self._local = threading.local()
        self._forbidden_streak = 0
        self._streak_lock = threading.Lock()

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
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            )
            proxies = self.settings.proxies()
            if proxies:
                session.proxies.update(proxies)
            self._local.session = session
        return session

    def close(self) -> None:
        """Закрывает сессию текущего потока."""
        session = getattr(self._local, "session", None)
        if session is not None:
            session.close()
            self._local.session = None

    # ------------------------------ запросы -------------------------------- #

    def _sleep_backoff(self, attempt: int) -> None:
        """Экспоненциальная задержка со «случайным дребезгом» между повторами."""
        delay = min(2.0 ** attempt, 30.0) + random.uniform(0.0, 0.75)
        logger.debug("Повтор через %.1f с", delay)
        time.sleep(delay)

    def _register_forbidden(self) -> None:
        """Считает подряд идущие 403 и при переполнении останавливает работу."""
        with self._streak_lock:
            self._forbidden_streak += 1
            streak = self._forbidden_streak
        if streak >= self.FORBIDDEN_TOLERANCE:
            self.quota.mark_exhausted(
                f"сервис вернул 403 подряд {streak} раз(а) — вероятна блокировка или капча"
            )

    def _register_success(self) -> None:
        with self._streak_lock:
            self._forbidden_streak = 0

    def _get(self, url: str, count_quota: bool) -> tuple[requests.Response | None, str, str]:
        """
        Выполняет GET-запрос со всеми повторами и обработкой ошибок.

        :param url:         адрес;
        :param count_quota: списывать ли единицу квоты за этот HTTP-запрос
                            (в режиме ``--count-http-requests``);
        :return: ``(ответ | None, статус, текст ошибки)``.
        """
        if count_quota and not self.quota.reserve():
            return None, STATUS_RATE_LIMITED, "исчерпана суточная квота запросов"

        last_error = ""
        for attempt in range(self.settings.max_retries + 1):
            self._rate_limiter.wait()
            try:
                response = self.session.get(
                    url,
                    timeout=self.settings.timeout,
                    allow_redirects=True,
                )
            except requests.exceptions.Timeout as exc:
                # Таймаут: запрос мог дойти до сервера, квоту не возвращаем.
                last_error = f"таймаут: {exc}"
                logger.debug("Таймаут %s (попытка %d)", url, attempt + 1)
                if attempt < self.settings.max_retries:
                    self._sleep_backoff(attempt)
                    continue
                return None, STATUS_ERROR, last_error
            except requests.exceptions.ConnectionError as exc:
                # Соединение не установлено — запрос до сервера не дошёл.
                last_error = f"ошибка соединения: {exc}"
                if count_quota:
                    self.quota.release()
                    count_quota = False
                if attempt < self.settings.max_retries:
                    self._sleep_backoff(attempt)
                    if not count_quota and self.quota.reserve():
                        count_quota = True
                    continue
                return None, STATUS_ERROR, last_error
            except requests.exceptions.RequestException as exc:
                last_error = f"ошибка запроса: {exc}"
                return None, STATUS_ERROR, last_error

            status_code = response.status_code

            if status_code == 200:
                self._register_success()
                return response, STATUS_OK, ""

            if status_code == 429:
                retry_after = response.headers.get("Retry-After", "")
                delay = 0.0
                try:
                    delay = float(retry_after)
                except (TypeError, ValueError):
                    delay = 0.0
                if 0 < delay <= 60 and attempt < self.settings.max_retries:
                    logger.warning("429 от checko.ru, ждём %.0f с по Retry-After", delay)
                    time.sleep(delay)
                    continue
                self.quota.mark_exhausted("HTTP 429 (Too Many Requests)")
                return response, STATUS_RATE_LIMITED, "HTTP 429: превышен лимит запросов"

            if status_code == 403:
                self._register_forbidden()
                return response, STATUS_FORBIDDEN, "HTTP 403: доступ запрещён"

            if status_code == 404:
                return response, STATUS_NOT_FOUND, "HTTP 404: страница не найдена"

            if 500 <= status_code < 600:
                last_error = f"HTTP {status_code}: ошибка сервера"
                if attempt < self.settings.max_retries:
                    self._sleep_backoff(attempt)
                    continue
                return response, STATUS_ERROR, last_error

            return response, STATUS_ERROR, f"HTTP {status_code}"

        return None, STATUS_ERROR, last_error or "неизвестная ошибка"

    # ------------------------------ поиск ---------------------------------- #

    def lookup(self, query: str, expected_inn: str = "") -> CheckoContacts:
        """
        Полный цикл: поиск компании -> открытие карточки -> разбор контактов.

        Единица суточной квоты списывается вызывающим кодом ДО вызова
        (одна компания = одна единица). В режиме ``--count-http-requests``
        дополнительный переход на карточку списывает ещё одну единицу.

        Никогда не выбрасывает исключений: любая проблема возвращается
        как результат со статусом ``error``/``forbidden``/``rate_limited``.
        """
        result = CheckoContacts(query=query, fetched_at=utcnow_iso(), attempts=1,
                                source=SOURCE_HTML)
        query = clean_text(query)
        if not query:
            result.status = STATUS_ERROR
            result.error = "пустой поисковый запрос"
            return result

        search_url = f"{CHECKO_BASE_URL}{CHECKO_SEARCH_PATH}?query={quote_plus(query)}"
        try:
            response, status, error = self._get(search_url, count_quota=False)
        except Exception as exc:  # noqa: BLE001 — клиент обязан быть «неубиваемым»
            result.status = STATUS_ERROR
            result.error = f"непредвиденная ошибка: {type(exc).__name__}: {exc}"
            logger.exception("Непредвиденная ошибка при запросе %s", query)
            return result

        if response is None or status != STATUS_OK:
            result.status = status
            result.error = error
            result.http_status = response.status_code if response is not None else None
            result.url = search_url
            return result

        result.http_status = response.status_code
        final_url = response.url
        html = response.text

        # Поиск мог сразу перенаправить на карточку компании.
        if _CARD_URL_RE.search(urlparse(final_url).path):
            parsed = parse_company_page(html, final_url, expected_inn)
            parsed.query = query
            parsed.http_status = response.status_code
            parsed.attempts = 1
            return parsed

        # Особые состояния страницы результатов.
        state = _detect_page_state(html)
        if state == STATUS_RATE_LIMITED:
            self.quota.mark_exhausted("страница сообщает об исчерпании лимита")
            result.status = STATUS_RATE_LIMITED
            result.error = "checko.ru сообщает об исчерпании суточного лимита"
            result.url = final_url
            return result
        if state == STATUS_FORBIDDEN:
            self._register_forbidden()
            result.status = STATUS_FORBIDDEN
            result.error = "checko.ru требует подтверждения (капча/блокировка)"
            result.url = final_url
            return result

        card_url = find_card_link(html, final_url)
        if not card_url:
            result.status = STATUS_NOT_FOUND
            result.error = "в результатах поиска нет карточки компании"
            result.url = final_url
            return result

        # Переход на карточку компании.
        try:
            card_response, card_status, card_error = self._get(
                card_url, count_quota=self.settings.count_http_requests
            )
        except Exception as exc:  # noqa: BLE001
            result.status = STATUS_ERROR
            result.error = f"непредвиденная ошибка: {type(exc).__name__}: {exc}"
            return result

        result.attempts = 2
        if card_response is None or card_status != STATUS_OK:
            result.status = card_status
            result.error = card_error
            result.url = card_url
            result.http_status = card_response.status_code if card_response is not None else None
            return result

        parsed = parse_company_page(card_response.text, card_url, expected_inn)
        parsed.query = query
        parsed.attempts = 2
        parsed.http_status = card_response.status_code
        if parsed.status == STATUS_RATE_LIMITED:
            self.quota.mark_exhausted("карточка сообщает об исчерпании лимита")
        return parsed
