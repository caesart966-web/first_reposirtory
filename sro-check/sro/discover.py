"""Поиск действующего адреса API, когда прошитые адреса перестали отвечать.

Зачем это нужно. У реестров НОСТРОЙ и НОПРИЗ нет опубликованного API, и они
меняют внутренние адреса без предупреждения — прошитый в программе адрес рано
или поздно начинает отдавать 404.

Что делает этот модуль. Ровно то же, что человек делает руками через F12:
берёт страницу реестра, вытаскивает из неё подключённые скрипты и ищет в них
строки, похожие на адреса API. Браузер для этого не нужен — хватает обычных
HTTP-запросов, поэтому работает и в собранной программе.

Модуль ничего не решает про членство в СРО: он только возвращает список
кандидатов, которые потом проверяются обычным путём.
"""

from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import urljoin, urlsplit

from .models import SOURCE_NOPRIZ, SOURCE_NOSTROY

# Страницы, с которых начинаем осмотр. Первой идёт страница поиска по членам:
# на ней скрипты реестра точно подключены.
# Реестр членов СРО открывается прямо в корне сайта — адресная строка так и
# остаётся «reestr.nostroy.ru», разделы переключаются вкладками внутри страницы.
PAGES: dict[str, list[str]] = {
    SOURCE_NOSTROY: [
        "https://reestr.nostroy.ru/",
        "https://reestr.nostroy.ru/reestr/chleny-sro",
    ],
    SOURCE_NOPRIZ: [
        "https://reestr.nopriz.ru/",
        "https://reestr.nopriz.ru/reestr/chleny-sro",
        "https://nopriz.ru/nreesters/",
    ],
}

_SCRIPT_SRC = re.compile(r"<script[^>]+src\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
# Любой путь в кавычках — из них берём хвосты вида «/member/list»
_ANY_PATH = re.compile(r"[\"'`](/[A-Za-z0-9_\-./]{3,})")
# Закрывающая кавычка намеренно не требуется: в коде сплошь и рядом пишут
# "/api/member/search?inn=" + inn — путь кончается на «?», а не на кавычке.
_RELATIVE_API = re.compile(r"[\"'`](/api/[A-Za-z0-9_\-./]{3,})")
_ABSOLUTE_API = re.compile(r"https?://[A-Za-z0-9_\-.]+/api/[A-Za-z0-9_\-./]{3,}")

# Слова, по которым видно, что путь ведёт к поиску по реестру…
# «list» стоит высоко не случайно: именно так называется запрос, которым сайт
# НОСТРОЙ берёт таблицу членов СРО.
_GOOD = (("member", 4), ("list", 3), ("search", 3), ("sro", 2), ("reestr", 1))
# …и по которым видно, что это что-то постороннее.
_BAD = ("auth", "login", "logout", "admin", "upload", "file", "image", "captcha",
        "token", "password", "feedback", "subscribe", "metric", "banner")

MAX_SCRIPTS = 12  # сколько скриптов осматривать — больше почти никогда не нужно
MAX_CANDIDATES = 6
MAX_BASES = 5  # ограничители склейки: иначе кандидатов станут сотни
MAX_FRAGMENTS = 8

# Сессия провайдера настроена на JSON («Accept: application/json»), а здесь мы
# просим обычную страницу и скрипты. С чужим Accept сервер вправе ответить 406
# или отдать не то, поэтому заголовки на этих запросах свои.
PAGE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
}


def score_path(path: str) -> int:
    """Насколько путь похож на поиск по членам реестра. Больше — правдоподобнее."""
    low = path.lower()
    if any(word in low for word in _BAD):
        return -1
    total = 0
    for word, weight in _GOOD:
        if word in low:
            total += weight
    return total


def _clean_matches(text: str, pattern: re.Pattern) -> set[str]:
    found: set[str] = set()
    for match in pattern.finditer(text):
        # Адрес с подстановкой (/api/member/${id}/card) использовать нельзя:
        # до неё путь оборван, а подставить в него нечего.
        if text[match.end() : match.end() + 1] in ("$", "{"):
            continue
        path = match.group(1) if pattern.groups else match.group(0)
        if "$" in path or "{" in path:
            continue
        found.add(path)
    return found


def api_paths(text: str) -> set[str]:
    """Вытащить из текста (HTML или JS) всё, что похоже на адрес API."""
    text = text or ""
    return _clean_matches(text, _RELATIVE_API) | _clean_matches(text, _ABSOLUTE_API)


def path_fragments(text: str) -> set[str]:
    """Куски пути, которые скрипт приклеивает к базовому адресу.

    Сайт редко хранит адрес целиком: в коде это `BASE + '/member/list'`.
    Поэтому отдельно собираем осмысленные хвосты — их потом склеим с базой.
    """
    text = text or ""
    fragments = set()
    for path in _clean_matches(text, _ANY_PATH):
        low = path.lower()
        if path.startswith("/api/"):
            continue  # это уже целый адрес, он собран отдельно
        if any(word in low for word in ("member", "list", "search")):
            fragments.add(path)
    return fragments


def combine(bases: Iterable[str], fragments: Iterable[str]) -> set[str]:
    """Склеить базовые адреса с хвостами: /api/sro/all + /member/list."""
    result = set()
    for base in list(bases)[:MAX_BASES]:
        trimmed = base.rstrip("/")
        for fragment in list(fragments)[:MAX_FRAGMENTS]:
            result.add(trimmed + fragment)
    return result


def script_urls(html: str, page_url: str) -> list[str]:
    """Адреса скриптов, подключённых на странице (уже абсолютные)."""
    urls: list[str] = []
    for src in _SCRIPT_SRC.findall(html or ""):
        absolute = urljoin(page_url, src)
        if absolute not in urls:
            urls.append(absolute)
    return urls


def to_absolute(path: str, page_url: str) -> str:
    return path if path.startswith("http") else urljoin(page_url, path)


def discover(source: str, session, timeout: float = 20.0, logger=print) -> list[str]:
    """Найти вероятные адреса API реестра.

    Возвращает список абсолютных адресов, самый правдоподобный — первым.
    Ошибки сети не выбрасываются наружу: не нашли так не нашли.
    """
    scored: dict[str, int] = {}

    for page_url in PAGES.get(source, []):
        try:
            response = session.get(page_url, timeout=timeout, headers=PAGE_HEADERS)
        except Exception as error:
            logger(f"[{source}] осмотр {page_url}: {type(error).__name__}")
            continue
        if response.status_code >= 400:
            logger(f"[{source}] осмотр {page_url}: HTTP {response.status_code}")
            continue

        html = response.text or ""
        sources = [(page_url, html)]

        for script_url in script_urls(html, page_url)[:MAX_SCRIPTS]:
            # Чужие домены (аналитика, рекламные сети) не осматриваем.
            if urlsplit(script_url).netloc != urlsplit(page_url).netloc:
                continue
            try:
                script = session.get(script_url, timeout=timeout, headers=PAGE_HEADERS)
            except Exception:
                continue
            if script.status_code < 400:
                sources.append((script_url, script.text or ""))

        for origin_url, text in sources:
            direct = api_paths(text)
            # Базы для склейки — те же найденные /api/-адреса: скрипт обычно
            # хранит основу и хвост порознь и соединяет их уже при запросе.
            glued = combine(sorted(direct), sorted(path_fragments(text)))
            for path in direct | glued:
                weight = score_path(path)
                if weight <= 0:
                    continue
                absolute = to_absolute(path, origin_url)
                scored[absolute] = max(scored.get(absolute, 0), weight)

        if scored:
            break  # первой страницы обычно достаточно

    best = sorted(scored, key=lambda url: (-scored[url], len(url)))[:MAX_CANDIDATES]
    if best:
        logger(f"[{source}] в скриптах сайта найдены возможные адреса API: {len(best)}")
        for url in best:
            logger(f"[{source}]    {url}")
    else:
        logger(f"[{source}] в скриптах сайта адресов API не нашлось")
    return best
