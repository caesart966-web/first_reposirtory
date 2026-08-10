"""Асинхронный HTTP-клиент приложения.

Обеспечивает (см. ТЗ, раздел 5 «Устойчивость работы»):
- ограничение частоты запросов на домен (token bucket, по умолчанию 5 rps);
- соблюдение robots.txt для обхода сайтов;
- экспоненциальный backoff 2/4/8/16/32 с (до 5 попыток) на 429/5xx и сетевых ошибках;
- корректный User-Agent с контактным адресом владельца;
- таймауты connect 10 с / read 30 с;
- кэш ответов в SQLite с TTL (повторный прогон не дёргает источники);
- пул HTTP-прокси из .env с проверкой живости перед стартом.

Никаких капча-солверов и обхода антибот-защит здесь нет и быть не должно:
если источник отвечает 403/капчей — вызывающий код помечает его недоступным.
"""
from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Any, Optional
from urllib import robotparser
from urllib.parse import urlsplit

import aiohttp

from core.config import Config
from storage.db import Database
from utils.logging_setup import get_logger


class FetchError(Exception):
    """Ошибка получения URL после всех повторов."""

    def __init__(self, message: str, url: str = "", status: Optional[int] = None,
                 retry_later: bool = False):
        super().__init__(message)
        self.url = url
        self.status = status
        self.retry_later = retry_later


class RobotsDisallowed(FetchError):
    """robots.txt запрещает доступ к URL — источник пропускаем, не обходим."""


@dataclass
class FetchResult:
    """Ответ HTTP (живой или из кэша)."""

    url: str
    status: int
    body: bytes
    content_type: str = ""
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def text(self) -> str:
        encodings = ["utf-8", "cp1251", "latin-1"]
        ct = (self.content_type or "").lower()
        if "charset=" in ct:
            declared = ct.split("charset=")[-1].split(";")[0].strip()
            if declared:
                encodings.insert(0, declared)
        for enc in encodings:
            try:
                return self.body.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        import json
        return json.loads(self.text)


class TokenBucket:
    """Ограничитель частоты запросов (запросов в секунду) на один хост."""

    def __init__(self, rate: float, capacity: Optional[float] = None):
        self.rate = max(rate, 0.1)
        self.capacity = capacity if capacity is not None else max(1.0, self.rate)
        self.tokens = self.capacity
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                await asyncio.sleep((1 - self.tokens) / self.rate)


_ROBOTS_ALLOW_ALL = object()   # маркер «robots.txt нет — всё разрешено»

_TRANSIENT_STATUSES = {429, 500, 502, 503, 504, 522, 524}
_NO_RETRY_STATUSES = {400, 401, 403, 404, 405, 410}


class HttpClient:
    """Единая точка всех внешних HTTP-запросов приложения."""

    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db
        self.log = get_logger()
        self._session: Optional[aiohttp.ClientSession] = None
        self._buckets: dict[str, TokenBucket] = {}
        self._buckets_lock = asyncio.Lock()
        self._robots: dict[str, Any] = {}
        self._robots_lock = asyncio.Lock()
        self._proxies: list[str] = []
        self._proxy_idx = 0
        self._per_host_rps = float(config.get("http.per_host_rps", 5.0))
        self._retries = int(config.get("http.retries", 5))
        self._respect_robots = bool(config.get("http.respect_robots", True))
        self._ttl = config.cache_ttl_seconds

    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        timeout = aiohttp.ClientTimeout(
            connect=float(self.config.get("http.connect_timeout", 10)),
            sock_read=float(self.config.get("http.read_timeout", 30)),
            total=None,
        )
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": self.config.user_agent},
            connector=aiohttp.TCPConnector(limit=50, ssl=False),
        )
        await self._check_proxies()

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def _check_proxies(self) -> None:
        """Проверить живость прокси из HTTP_PROXY_POOL перед стартом."""
        pool = self.config.proxy_pool()
        if not pool:
            return
        check_url = self.config.get("http.proxy_check_url")
        alive: list[str] = []
        for proxy in pool:
            try:
                assert self._session is not None
                async with self._session.get(
                    check_url, proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status < 500:
                        alive.append(proxy)
                        self.log.info("Прокси живой: %s", _mask_proxy(proxy))
                    else:
                        self.log.warning("Прокси отвечает %s: %s", resp.status, _mask_proxy(proxy))
            except Exception as exc:  # noqa: BLE001 — любая ошибка = мёртвый прокси
                self.log.warning("Прокси недоступен (%s): %s", exc.__class__.__name__, _mask_proxy(proxy))
        self._proxies = alive
        if pool and not alive:
            self.log.warning("Все прокси из пула мертвы — работаем напрямую")

    def _next_proxy(self) -> Optional[str]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._proxy_idx % len(self._proxies)]
        self._proxy_idx += 1
        return proxy

    # ------------------------------------------------------------------ #

    async def _bucket_for(self, host: str) -> TokenBucket:
        async with self._buckets_lock:
            bucket = self._buckets.get(host)
            if bucket is None:
                bucket = TokenBucket(self._per_host_rps)
                self._buckets[host] = bucket
            return bucket

    async def allowed_by_robots(self, url: str) -> bool:
        """Проверить robots.txt хоста (кэшируется на время прогона и в HTTP-кэше)."""
        if not self._respect_robots:
            return True
        parts = urlsplit(url)
        host_key = f"{parts.scheme}://{parts.netloc}"
        async with self._robots_lock:
            cached = self._robots.get(host_key)
        if cached is None:
            robots_url = f"{host_key}/robots.txt"
            parser: Any = _ROBOTS_ALLOW_ALL
            try:
                result = await self._fetch_raw(
                    robots_url, check_robots=False, use_cache=True,
                    cache_ttl=86400, max_retries=1,
                )
                if result.status == 200 and result.body:
                    rp = robotparser.RobotFileParser()
                    rp.parse(result.text.splitlines())
                    parser = rp
            except FetchError:
                parser = _ROBOTS_ALLOW_ALL  # robots не отдался — не блокируемся
            async with self._robots_lock:
                self._robots[host_key] = parser
            cached = parser
        if cached is _ROBOTS_ALLOW_ALL:
            return True
        agent = self.config.get("app.user_agent", "ContactFinderBot").split("/")[0]
        try:
            return bool(cached.can_fetch(agent, url) or cached.can_fetch("*", url))
        except Exception:  # noqa: BLE001 — битый robots.txt не должен ронять прогон
            return True

    # ------------------------------------------------------------------ #

    @staticmethod
    def _cache_key(method: str, url: str, params: Optional[dict],
                   payload: Optional[bytes]) -> str:
        h = hashlib.sha256()
        h.update(method.upper().encode())
        h.update(url.encode())
        if params:
            h.update(str(sorted(params.items())).encode())
        if payload:
            h.update(payload)
        return h.hexdigest()

    async def fetch(self, url: str, *, method: str = "GET",
                    params: Optional[dict] = None,
                    data: Optional[dict] = None,
                    json_body: Optional[Any] = None,
                    headers: Optional[dict[str, str]] = None,
                    check_robots: bool = False,
                    use_cache: bool = True,
                    cache_ttl: Optional[int] = None,
                    max_retries: Optional[int] = None) -> FetchResult:
        """Получить URL со всеми ограничениями вежливости.

        Бросает RobotsDisallowed, если robots.txt запрещает путь, и FetchError
        после исчерпания повторов (retry_later=True для 429/5xx/сети).
        """
        if check_robots and not await self.allowed_by_robots(url):
            raise RobotsDisallowed(f"robots.txt запрещает {url}", url=url)
        return await self._fetch_raw(
            url, method=method, params=params, data=data, json_body=json_body,
            headers=headers, check_robots=False, use_cache=use_cache,
            cache_ttl=cache_ttl, max_retries=max_retries,
        )

    async def _fetch_raw(self, url: str, *, method: str = "GET",
                         params: Optional[dict] = None,
                         data: Optional[dict] = None,
                         json_body: Optional[Any] = None,
                         headers: Optional[dict[str, str]] = None,
                         check_robots: bool = False,  # noqa: ARG002 — сигнатура едина
                         use_cache: bool = True,
                         cache_ttl: Optional[int] = None,
                         max_retries: Optional[int] = None) -> FetchResult:
        if self._session is None:
            raise FetchError("HTTP-клиент не запущен (нет вызова start())", url=url)

        payload_bytes: Optional[bytes] = None
        if json_body is not None:
            import json as _json
            payload_bytes = _json.dumps(json_body, ensure_ascii=False, sort_keys=True).encode()
        elif data is not None:
            payload_bytes = str(sorted(data.items())).encode()

        key = self._cache_key(method, url, params, payload_bytes)
        ttl = cache_ttl if cache_ttl is not None else self._ttl
        if use_cache:
            row = self.db.cache_get(key, ttl)
            if row is not None:
                return FetchResult(
                    url=row["url"] or url, status=int(row["status"]),
                    body=row["body"] or b"", content_type=row["content_type"] or "",
                    from_cache=True,
                )

        host = urlsplit(url).netloc
        bucket = await self._bucket_for(host)

        delays = self.config.backoff_delays
        attempts = max_retries if max_retries is not None else self._retries
        last_error: Optional[str] = None
        last_status: Optional[int] = None

        for attempt in range(attempts):
            await bucket.acquire()
            try:
                async with self._session.request(
                    method, url, params=params, data=data, json=json_body,
                    headers=headers, proxy=self._next_proxy(),
                    allow_redirects=True, max_redirects=5,
                ) as resp:
                    body = await resp.read()
                    result = FetchResult(
                        url=str(resp.url), status=resp.status, body=body,
                        content_type=resp.headers.get("Content-Type", ""),
                    )
                    if resp.status in _TRANSIENT_STATUSES:
                        last_error = f"HTTP {resp.status}"
                        last_status = resp.status
                        raise _Transient(last_error)
                    if result.ok and use_cache:
                        self.db.cache_put(key, url, result.status, body, result.content_type)
                    return result
            except _Transient:
                pass
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                last_error = f"{exc.__class__.__name__}: {exc}"
                last_status = None
            if attempt < attempts - 1:
                delay = delays[min(attempt, len(delays) - 1)]
                self.log.debug("Повтор %s через %.0f с (%s), попытка %d/%d",
                               url, delay, last_error, attempt + 2, attempts)
                await asyncio.sleep(delay)

        raise FetchError(
            f"не удалось получить {url}: {last_error}", url=url,
            status=last_status, retry_later=True,
        )


class _Transient(Exception):
    """Внутренний маркер временной ошибки (429/5xx) для цикла повторов."""


def _mask_proxy(proxy: str) -> str:
    """Скрыть логин/пароль прокси в логах."""
    if "@" in proxy:
        scheme, _, rest = proxy.partition("://")
        creds, _, hostpart = rest.rpartition("@")
        return f"{scheme}://***@{hostpart}" if creds else proxy
    return proxy
