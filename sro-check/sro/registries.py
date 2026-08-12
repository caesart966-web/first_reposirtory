"""Обращение к реестрам НОСТРОЙ и НОПРИЗ по ИНН.

Главный принцип файла: программа имеет право написать «нет» ТОЛЬКО если
реестр ответил, ответ разобран и в нём достоверно нет записей по этому ИНН.
Любая неопределённость (сайт не ответил, вернул HTML вместо JSON, вернул JSON
незнакомой структуры, вернул записи без поля ИНН) — это Outcome.UNKNOWN,
то есть «не удалось проверить».

Почему так сложно с эндпоинтами. У реестров нет опубликованного и
гарантированно стабильного API. Поэтому здесь описан СПИСОК вариантов
запроса; программа пробует их по очереди, запоминает первый рабочий и дальше
использует только его. Найти рабочий вариант вручную можно командой
    python check_sro.py --probe <ИНН>
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Iterator
from urllib.parse import urlsplit

import requests

from .inn import normalize_inn
from .models import (
    SOURCE_NOPRIZ,
    SOURCE_NOSTROY,
    Membership,
    Outcome,
    RegistryAnswer,
)

# ---------------------------------------------------------------------------
# Описание вариантов запроса
# ---------------------------------------------------------------------------


@dataclass
class Endpoint:
    """Один вариант обращения к реестру."""

    name: str
    method: str  # GET или POST
    url: str
    params: Callable[[str], dict] | None = None  # query-параметры
    json_body: Callable[[str], dict] | None = None  # тело POST-запроса
    referer: str = ""

    def build(self, inn: str) -> dict:
        kwargs: dict[str, Any] = {}
        if self.params is not None:
            kwargs["params"] = self.params(inn)
        if self.json_body is not None:
            kwargs["json"] = self.json_body(inn)
        return kwargs


def origin_of(url: str) -> str:
    """Схема и домен адреса: «https://reestr.nostroy.ru».

    Отдельной функцией — потому что наивное отрезание по строке здесь ошибается:
    в адресе `https://reestr.nostroy.ru/reestr/...` подстрока `/reestr`
    впервые встречается ещё в домене, и Origin получался обрубком `https:/`.
    """
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return ""
    return f"{parts.scheme}://{parts.netloc}"


def _body_hint(response) -> str:
    """Короткая выжимка из тела ответа.

    При 4xx/5xx сервер обычно пишет в теле, что именно ему не понравилось,
    — без этого «HTTP 404» не даёт ничего для починки.
    """
    try:
        text = (response.text or "").strip()
    except Exception:
        return ""
    if not text:
        return ""
    return " — " + re.sub(r"\s+", " ", text)[:200]


def _search_params(inn: str) -> dict:
    return {"inn": inn}


def _search_string_params(inn: str) -> dict:
    return {"searchString": inn, "page": 1, "pageCount": 50}


def _search_string_body(inn: str) -> dict:
    return {"searchString": inn, "page": 1, "pageCount": 50}


NOSTROY_SITE = "https://reestr.nostroy.ru"
NOPRIZ_SITE = "https://reestr.nopriz.ru"

NOSTROY_ENDPOINTS: list[Endpoint] = [
    Endpoint(
        "nostroy:get-inn",
        "GET",
        f"{NOSTROY_SITE}/api/sro/all/member/search",
        params=_search_params,
        referer=f"{NOSTROY_SITE}/reestr/chleny-sro",
    ),
    Endpoint(
        "nostroy:get-searchString",
        "GET",
        f"{NOSTROY_SITE}/api/sro/all/member/search",
        params=_search_string_params,
        referer=f"{NOSTROY_SITE}/reestr/chleny-sro",
    ),
    Endpoint(
        "nostroy:post-searchString",
        "POST",
        f"{NOSTROY_SITE}/api/sro/all/member/search",
        json_body=_search_string_body,
        referer=f"{NOSTROY_SITE}/reestr/chleny-sro",
    ),
    Endpoint(
        "nostroy:get-member-inn",
        "GET",
        f"{NOSTROY_SITE}/api/member/search",
        params=_search_params,
        referer=f"{NOSTROY_SITE}/reestr/chleny-sro",
    ),
]

NOPRIZ_ENDPOINTS: list[Endpoint] = [
    Endpoint(
        "nopriz:get-inn",
        "GET",
        f"{NOPRIZ_SITE}/api/sro/all/member/search",
        params=_search_params,
        referer=f"{NOPRIZ_SITE}/reestr/chleny-sro",
    ),
    Endpoint(
        "nopriz:get-searchString",
        "GET",
        f"{NOPRIZ_SITE}/api/sro/all/member/search",
        params=_search_string_params,
        referer=f"{NOPRIZ_SITE}/reestr/chleny-sro",
    ),
    Endpoint(
        "nopriz:post-searchString",
        "POST",
        f"{NOPRIZ_SITE}/api/sro/all/member/search",
        json_body=_search_string_body,
        referer=f"{NOPRIZ_SITE}/reestr/chleny-sro",
    ),
    Endpoint(
        "nopriz:www-get-inn",
        "GET",
        "https://nopriz.ru/api/sro/all/member/search",
        params=_search_params,
        referer="https://nopriz.ru/nreesters/",
    ),
]


# ---------------------------------------------------------------------------
# Разбор произвольного JSON-ответа
# ---------------------------------------------------------------------------

_INN_KEY = re.compile(r"(^|_)inn($|_)|инн", re.IGNORECASE)
_SRO_SCOPE = re.compile(r"sro|partnership|np_|self_regul", re.IGNORECASE)

# Ключи-контейнеры, в которых обычно лежит список записей
_LIST_KEYS = ("data", "items", "results", "result", "rows", "list", "content", "members", "records")
# Ключи, в которых обычно лежит общее число найденного
_COUNT_KEYS = ("count", "total", "totalCount", "total_count", "totalElements", "recordsTotal")


def _leaves(obj: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Пройти по вложенному JSON и вернуть все скалярные значения с их путями.

    Путь — строка вида "sro.full_description". По нему потом опознаём поля.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _leaves(value, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _leaves(value, f"{prefix}.{index}" if prefix else str(index))
    else:
        if obj is not None and obj != "":
            yield prefix, obj


def _find_record_lists(obj: Any, depth: int = 0) -> list[tuple[str, list]]:
    """Найти в ответе все списки, похожие на списки записей реестра.

    Возвращает пары (путь, список). Пустые списки тоже возвращаются — пустой
    список по известному пути это и есть достоверное «ничего не найдено».
    """
    found: list[tuple[str, list]] = []

    def walk(node: Any, path: str, level: int) -> None:
        if level > 6:
            return
        if isinstance(node, list):
            # Список записей — это список словарей (или пустой список).
            if not node or all(isinstance(item, dict) for item in node):
                found.append((path, node))
            return
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else str(key), level + 1)

    walk(obj, "", depth)

    # Приоритет — спискам, лежащим в типичных контейнерах (data/items/...).
    def rank(item: tuple[str, list]) -> tuple[int, int]:
        path, _ = item
        last = path.split(".")[-1].lower() if path else ""
        known = 0 if last in _LIST_KEYS else 1
        return (known, path.count("."))

    found.sort(key=rank)
    return found


def _find_count(obj: Any) -> int | None:
    """Найти в ответе поле с общим числом найденных записей."""
    if not isinstance(obj, dict):
        return None
    for key in _COUNT_KEYS:
        if key in obj and isinstance(obj[key], int):
            return obj[key]
    for value in obj.values():
        if isinstance(value, dict):
            nested = _find_count(value)
            if nested is not None:
                return nested
    return None


def _record_inns(record: dict) -> tuple[list[str], list[str]]:
    """Вытащить из записи все ИНН.

    Возвращает (инн_компании, все_инн). Разделение нужно потому, что в записи
    обычно есть и ИНН члена СРО, и ИНН самой СРО — совпадение по второму
    ничего не доказывает.
    """
    member: list[str] = []
    every: list[str] = []
    for path, value in _leaves(record):
        last = path.split(".")[-1]
        if not _INN_KEY.search(last):
            continue
        digits = normalize_inn(value)
        if not digits:
            continue
        every.append(digits)
        scope = ".".join(path.split(".")[:-1])
        if not _SRO_SCOPE.search(scope):
            member.append(digits)
    return member, every


def _pick(record: dict, patterns: Iterable[str]) -> str | None:
    """Взять из записи первое значение, чей путь подходит под один из шаблонов.

    Шаблоны перечислены по убыванию приоритета.
    """
    leaves = [(path.lower(), path, value) for path, value in _leaves(record)]
    for pattern in patterns:
        regex = re.compile(pattern, re.IGNORECASE)
        for lowered, _path, value in leaves:
            if regex.search(lowered) and isinstance(value, (str, int, float)):
                text = str(value).strip()
                if text:
                    return text
    return None


_SRO_NAME_PATTERNS = (
    r"^sro\.(full_description|full_name|name|title|short_description|short_name)$",
    r"sro.*(full_description|full_name|short_description)",
    r"sro.*(name|title)",
    r"(partnership|np_name|self_regul).*(name|description|title)",
    r"^(sro_name|sroname|organization_name)$",
)

_REG_NUMBER_PATTERNS = (
    r"^(registry_number|reg_number|member_number|number_in_registry)$",
    r"(member|memb).*(number|nomer)",
    r"^(registration_number|reestr_number|number)$",
    r"(registry|reestr).*(number|nomer)",
    r"^sro\.(registration_number|reg_number|number)$",
)

_STATUS_PATTERNS = (
    r"^(member_status|membership_status|status_name|status_description)$",
    r"^status$",
    r"(member|membership).*(status|state)",
    r"status.*(name|description|title)",
    r"status",
)


def _membership_from_record(record: dict, source: str) -> Membership:
    return Membership(
        source=source,
        sro_name=_pick(record, _SRO_NAME_PATTERNS),
        registry_number=_pick(record, _REG_NUMBER_PATTERNS),
        status_raw=_pick(record, _STATUS_PATTERNS),
    )


def interpret_payload(payload: Any, inn: str, source: str) -> RegistryAnswer:
    """Превратить разобранный JSON в вердикт по одному реестру.

    Это самая ответственная функция программы, поэтому решения принимаются
    консервативно: любое сомнение трактуется как «не удалось проверить».
    """
    if payload is None:
        return RegistryAnswer(source, Outcome.UNKNOWN, note="пустой ответ")

    if not isinstance(payload, (dict, list)):
        return RegistryAnswer(source, Outcome.UNKNOWN, note="ответ не похож на данные реестра")

    # Некоторые API отвечают {"success": false, "message": "..."}
    if isinstance(payload, dict):
        success = payload.get("success")
        if success is False:
            message = payload.get("message") or payload.get("error") or "реестр вернул отказ"
            return RegistryAnswer(source, Outcome.UNKNOWN, note=str(message)[:200])

    candidates = _find_record_lists(payload)
    if not candidates:
        return RegistryAnswer(
            source, Outcome.UNKNOWN, note="в ответе не найден список записей (структура изменилась?)"
        )

    path, records = candidates[0]

    if not records:
        # Пустой список — достоверное «ничего не найдено», но только если это
        # действительно контейнер данных, а не случайный пустой список.
        last = path.split(".")[-1].lower() if path else ""
        if last in _LIST_KEYS or path == "":
            count = _find_count(payload)
            if count in (None, 0):
                return RegistryAnswer(source, Outcome.EMPTY, note=f"пусто по пути «{path or '[]'}»")
            return RegistryAnswer(
                source,
                Outcome.UNKNOWN,
                note=f"противоречие: записей нет, но счётчик = {count}",
            )
        return RegistryAnswer(
            source, Outcome.UNKNOWN, note=f"пустой список по неизвестному пути «{path}»"
        )

    # Список не пуст — обязательно сверяем ИНН. Поиск мог сработать не по ИНН
    # или вовсе проигнорировать параметр и вернуть весь реестр; без этой сверки
    # мы бы приняли «первая страница реестра» за «компании здесь нет».
    matched: list[dict] = []
    saw_inn_field = False
    ambiguous_hit = False
    for record in records:
        member_inns, every_inn = _record_inns(record)
        if member_inns or every_inn:
            saw_inn_field = True
        if inn in member_inns:
            matched.append(record)
        elif inn in every_inn:
            # ИНН нашёлся, но в поле, похожем на реквизиты самой СРО. Это не
            # доказывает членство, но и «нет» здесь писать нельзя.
            ambiguous_hit = True

    if not saw_inn_field:
        return RegistryAnswer(
            source,
            Outcome.UNKNOWN,
            note=f"в записях нет поля ИНН — не могу подтвердить совпадение ({len(records)} записей)",
        )

    if matched:
        memberships = [_membership_from_record(record, source) for record in matched]
        return RegistryAnswer(source, Outcome.FOUND, memberships=memberships)

    if ambiguous_hit:
        return RegistryAnswer(
            source,
            Outcome.UNKNOWN,
            note="ИНН встречается в ответе, но не в поле компании — нужна ручная проверка",
        )

    # Совпадений нет. Прежде чем писать «нет», убеждаемся, что реестр
    # действительно искал по нашему ИНН, а не отдал общий список.
    count = _find_count(payload)
    if len(records) > 5:
        return RegistryAnswer(
            source,
            Outcome.UNKNOWN,
            note=(
                f"реестр вернул {len(records)} чужих записей — похоже, поиск "
                "не отфильтровал по ИНН"
            ),
        )
    if count is not None and count > len(records):
        return RegistryAnswer(
            source,
            Outcome.UNKNOWN,
            note=f"показана лишь часть результатов ({len(records)} из {count}) — нужен точный поиск",
        )

    return RegistryAnswer(
        source,
        Outcome.EMPTY,
        note=f"реестр вернул {len(records)} записей, ни одна не с этим ИНН",
    )


# ---------------------------------------------------------------------------
# HTTP-клиент
# ---------------------------------------------------------------------------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}


class RegistryProvider:
    """Опрос одного реестра с перебором вариантов эндпоинта."""

    def __init__(
        self,
        source: str,
        endpoints: list[Endpoint],
        timeout: float = 25.0,
        attempts: int = 3,
        session: requests.Session | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.source = source
        self.endpoints = list(endpoints)
        self.timeout = timeout
        self.attempts = attempts
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.logger = logger or (lambda message: None)
        # Эндпоинт, который уже доказал работоспособность. Пока он не найден,
        # перебираем все варианты; после — обращаемся только к нему.
        self.working: Endpoint | None = None
        self.disabled_reason: str = ""

    # -- низкий уровень -----------------------------------------------------

    def _request(self, endpoint: Endpoint, inn: str) -> tuple[Any | None, str]:
        """Выполнить запрос. Возвращает (payload или None, пояснение)."""
        kwargs = endpoint.build(inn)
        headers = dict(DEFAULT_HEADERS)
        if endpoint.referer:
            headers["Referer"] = endpoint.referer
            origin = origin_of(endpoint.referer)
            if origin:
                headers["Origin"] = origin

        last_note = ""
        for attempt in range(1, self.attempts + 1):
            try:
                response = self.session.request(
                    endpoint.method,
                    endpoint.url,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                )
            except requests.RequestException as error:
                last_note = f"сеть: {type(error).__name__}"
                if attempt < self.attempts:
                    time.sleep(2 ** attempt)
                continue

            if response.status_code == 429:
                last_note = "реестр просит снизить темп (429)"
                if attempt < self.attempts:
                    time.sleep(10 * attempt)
                continue

            if response.status_code >= 500:
                last_note = f"ошибка сервера {response.status_code}{_body_hint(response)}"
                if attempt < self.attempts:
                    time.sleep(2 ** attempt)
                continue

            if response.status_code >= 400:
                return None, f"HTTP {response.status_code}{_body_hint(response)}"

            content_type = response.headers.get("Content-Type", "")
            body = response.text or ""
            if "json" not in content_type.lower():
                # HTML вместо JSON — обычно означает заглушку, капчу или
                # изменившийся адрес. Это НЕ «нет СРО».
                snippet = re.sub(r"\s+", " ", body[:120]).strip()
                if body.lstrip()[:1] not in ("{", "["):
                    return None, f"вместо JSON пришёл {content_type or 'неизвестный формат'}: {snippet}"

            try:
                return response.json(), ""
            except (ValueError, json.JSONDecodeError):
                return None, "ответ не разобрался как JSON"

        return None, last_note or "не удалось выполнить запрос"

    # -- высокий уровень ----------------------------------------------------

    def lookup(self, inn: str) -> RegistryAnswer:
        """Проверить один ИНН в этом реестре."""
        if self.working is not None:
            payload, note = self._request(self.working, inn)
            if payload is None:
                return RegistryAnswer(self.source, Outcome.UNKNOWN, note=note)
            answer = interpret_payload(payload, inn, self.source)
            if answer.outcome is Outcome.UNKNOWN:
                # Ранее рабочий эндпоинт вдруг перестал пониматься — перестаём
                # ему доверять и в следующий раз снова переберём варианты.
                self.logger(
                    f"[{self.source}] эндпоинт {self.working.name} перестал давать понятный ответ: {answer.note}"
                )
                self.working = None
            return answer

        reasons: list[str] = []
        for endpoint in self.endpoints:
            payload, note = self._request(endpoint, inn)
            if payload is None:
                reasons.append(note)
                continue
            answer = interpret_payload(payload, inn, self.source)
            if answer.outcome is Outcome.UNKNOWN:
                reasons.append(answer.note)
                continue
            # Эндпоинт вернул понятный ответ — запоминаем его как рабочий.
            self.working = endpoint
            self.logger(f"[{self.source}] рабочий эндпоинт: {endpoint.name}")
            return answer

        # В примечание для человека пишем причину, а не внутренние имена
        # эндпоинтов: одинаковые причины схлопываем, чтобы не было простыней.
        unique = list(dict.fromkeys(reason for reason in reasons if reason))
        return RegistryAnswer(
            self.source,
            Outcome.UNKNOWN,
            note="; ".join(unique[:2])[:200] or "реестр не ответил",
        )

    def probe(self, inn: str) -> list[dict]:
        """Диагностика: попробовать все варианты и рассказать, что вышло."""
        report: list[dict] = []
        for endpoint in self.endpoints:
            payload, note = self._request(endpoint, inn)
            row: dict[str, Any] = {"endpoint": endpoint.name, "url": endpoint.url}
            if payload is None:
                row["result"] = "нет ответа"
                row["note"] = note
            else:
                answer = interpret_payload(payload, inn, self.source)
                row["result"] = answer.outcome.value
                row["note"] = answer.note
                row["sample"] = json.dumps(payload, ensure_ascii=False)[:400]
                if answer.memberships:
                    row["found"] = [m.to_dict() for m in answer.memberships]
            report.append(row)
        return report


def build_providers(
    timeout: float = 25.0,
    attempts: int = 3,
    logger: Callable[[str], None] | None = None,
    nostroy_url: str = "",
    nopriz_url: str = "",
) -> dict[str, RegistryProvider]:
    """Собрать провайдеров обоих реестров.

    nostroy_url / nopriz_url — возможность вручную задать адрес API
    (например, найденный через --probe или подсмотренный в браузере).
    """
    nostroy_endpoints = list(NOSTROY_ENDPOINTS)
    nopriz_endpoints = list(NOPRIZ_ENDPOINTS)

    # Заданный вручную адрес считаем единственно верным: перебирать после него
    # догадки бессмысленно и только замедляет работу. На безопасность это не
    # влияет — сбой такого эндпоинта всё равно даёт «не удалось проверить».
    if nostroy_url:
        nostroy_endpoints = [Endpoint("nostroy:custom", "GET", nostroy_url, params=_search_params)]
    if nopriz_url:
        nopriz_endpoints = [Endpoint("nopriz:custom", "GET", nopriz_url, params=_search_params)]

    return {
        SOURCE_NOSTROY: RegistryProvider(
            SOURCE_NOSTROY, nostroy_endpoints, timeout, attempts, logger=logger
        ),
        SOURCE_NOPRIZ: RegistryProvider(
            SOURCE_NOPRIZ, nopriz_endpoints, timeout, attempts, logger=logger
        ),
    }
