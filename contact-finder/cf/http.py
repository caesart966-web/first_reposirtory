"""HTTP-клиент: ретраи, троттлинг, ротация User-Agent, дружелюбие к robots.

Работает на голой стандартной библиотеке (urllib), чтобы запускалось из
коробки без pip install. Если установлен requests — использует его (лучше
с TLS и редиректами), но это не обязательно.
"""
from __future__ import annotations

import gzip
import random
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

from .secrets import scrub

_SECRET_PARAMS = {"key", "apikey", "api_key", "token", "access_token",
                   "secret", "password", "pwd", "auth"}

try:  # requests лучше держит TLS/редиректы, но не обязателен
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:  # noqa: BLE001
    _HAS_REQUESTS = False

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class Fetcher:
    """Одна точка входа для всех сетевых запросов проекта."""

    def __init__(
        self,
        *,
        delay: float = 1.5,
        timeout: float = 25.0,
        retries: int = 3,
        proxy: str | None = None,
        verbose: bool = False,
    ) -> None:
        self.delay = delay
        self.timeout = timeout
        self.retries = retries
        self.proxy = proxy
        self.verbose = verbose
        self._last_call = 0.0
        self._session = requests.Session() if _HAS_REQUESTS else None
        # Счётчик подряд идущих отказов по каждому хосту. Если сайт лежит или
        # рвёт соединение, нет смысла долбить его десятком путей подряд:
        # после _DEAD_AFTER неудач хост исключается до конца прогона.
        self._host_failures: dict[str, int] = {}
        self._dead_hosts: set[str] = set()
        self._last_error_was_limit = False

    _DEAD_AFTER = 2  # столько неудачных URL подряд — и хост считается мёртвым

    @staticmethod
    def _host_of(url: str) -> str:
        try:
            return urllib.parse.urlparse(url).netloc.lower()
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def safe_url(url: str) -> str:
        """URL без секретов — для вывода в лог.

        API-ключи передаются в query-строке, а лог пользователь копирует в
        переписку, скриншоты и баг-репорты. Значения параметров key/token/
        apikey/secret/password заменяются на «***».
        """
        try:
            parts = urllib.parse.urlsplit(url)
            if not parts.query:
                return url
            pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
            masked = [
                (k, "***" if k.lower() in _SECRET_PARAMS else v) for k, v in pairs
            ]
            return urllib.parse.urlunsplit(
                (parts.scheme, parts.netloc, parts.path,
                 urllib.parse.urlencode(masked), parts.fragment)
            )
        except Exception:  # noqa: BLE001
            return url

    # ------------------------------------------------------------------ утилиты

    def _throttle(self) -> None:
        """Не бьём один хост чаще, чем раз в self.delay секунд (+джиттер)."""
        wait = self.delay + random.uniform(0, self.delay)
        elapsed = time.time() - self._last_call
        if elapsed < wait:
            time.sleep(wait - elapsed)
        self._last_call = time.time()

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "close",
        }

    # ------------------------------------------------------------------ запрос

    def get(self, url: str) -> str | None:
        """GET с ретраями и экспоненциальной паузой. None — если не удалось."""
        host = self._host_of(url)

        # Хост уже признан мёртвым — не тратим на него время.
        if host in self._dead_hosts:
            if self.verbose:
                print(scrub(f"    · пропуск {self.safe_url(url)} — хост {host} недоступен"))
            return None

        for attempt in range(1, self.retries + 1):
            self._throttle()
            try:
                result = self._get_requests(url) if self._session is not None else self._get_urllib(url)
                self._host_failures.pop(host, None)  # хост живой — сбрасываем счётчик
                return result
            except Exception as exc:  # noqa: BLE001
                self._last_error_was_limit = "блок/лимит" in str(exc)
                if self.verbose:
                    print(scrub(f"    ! попытка {attempt}/{self.retries} {self.safe_url(url)} — {exc}"))
                if attempt < self.retries:
                    time.sleep(2 ** attempt)

        # Все попытки исчерпаны — засчитываем хосту неудачу.
        self._host_failures[host] = self._host_failures.get(host, 0) + 1
        if self._host_failures[host] >= self._DEAD_AFTER:
            self._dead_hosts.add(host)
            if self.verbose:
                # 403/429 от API — это почти всегда исчерпанный лимит, а не
                # падение сайта. Пишем прямо, иначе человек ищет проблему с сетью.
                if self._last_error_was_limit:
                    print(f"    × {host}: исчерпан лимит запросов — "
                          f"дальше пропускаем, продолжите завтра")
                else:
                    print(f"    × хост {host} исключён до конца прогона (не отвечает)")
        return None

    def _get_requests(self, url: str) -> str | None:
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        resp = self._session.get(  # type: ignore[union-attr]
            url,
            headers=self._headers(),
            timeout=self.timeout,
            proxies=proxies,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        if resp.status_code in (403, 429):
            raise RuntimeError(f"HTTP {resp.status_code} (блок/лимит)")
        return None

    def _get_urllib(self, url: str) -> str | None:
        opener_args: list = []
        if self.proxy:
            opener_args.append(
                urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy})
            )
        opener = urllib.request.build_opener(*opener_args)
        req = urllib.request.Request(url, headers=self._headers())
        with opener.open(req, timeout=self.timeout) as resp:
            raw = resp.read()
            enc = resp.headers.get("Content-Encoding", "")
            if enc == "gzip":
                raw = gzip.decompress(raw)
            elif enc == "deflate":
                raw = zlib.decompress(raw)
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
