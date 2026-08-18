"""Вежливый асинхронный HTTP-клиент: robots.txt, лимит частоты, кэш, ретраи.

Три причины, почему нельзя просто дёргать httpx.get в цикле:
1) без задержек между запросами сайт банит IP на десятом URL;
2) без кэша каждый повторный прогон — это новая нагрузка на чужой сервер;
3) без учёта robots.txt сбор данных перестаёт быть добросовестным.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

log = logging.getLogger("company_intel.http")

DEFAULT_UA = (
    "company-intel/0.1 (+https://github.com/caesart966-web/first_reposirtory; "
    "research contact-discovery bot)"
)


@dataclass
class Response:
    url: str
    status: int
    text: str
    headers: dict[str, str]
    from_cache: bool = False

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self):
        return json.loads(self.text)


class ResponseCache:
    """SQLite-кэш ответов: одинаковый URL в пределах TTL не запрашивается дважды."""

    def __init__(self, path: str | Path | None, ttl_seconds: int = 86_400) -> None:
        self.ttl = ttl_seconds
        self.conn: sqlite3.Connection | None = None
        if path is None:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS http_cache (
                   key TEXT PRIMARY KEY, url TEXT, status INTEGER,
                   body TEXT, headers TEXT, fetched_at REAL)"""
        )
        self.conn.commit()

    @staticmethod
    def _key(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def get(self, url: str) -> Response | None:
        if not self.conn:
            return None
        row = self.conn.execute(
            "SELECT status, body, headers, fetched_at FROM http_cache WHERE key = ?",
            (self._key(url),),
        ).fetchone()
        if not row:
            return None
        status, body, headers, fetched_at = row
        if time.time() - fetched_at > self.ttl:
            return None
        return Response(url, status, body, json.loads(headers), from_cache=True)

    def put(self, resp: Response) -> None:
        if not self.conn:
            return
        self.conn.execute(
            "INSERT OR REPLACE INTO http_cache VALUES (?,?,?,?,?,?)",
            (self._key(resp.url), resp.url, resp.status, resp.text,
             json.dumps(resp.headers), time.time()),
        )
        self.conn.commit()

    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None


class Fetcher:
    """Один клиент на весь прогон: общий кэш, лимиты и статистика."""

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_UA,
        timeout: float = 20.0,
        per_host_delay: float = 1.0,
        max_concurrency: int = 8,
        respect_robots: bool = True,
        cache_path: str | Path | None = None,
        cache_ttl: int = 86_400,
        max_bytes: int = 3_000_000,
        max_retries: int = 3,
    ) -> None:
        self.user_agent = user_agent
        self.per_host_delay = per_host_delay
        self.respect_robots = respect_robots
        self.max_bytes = max_bytes
        self.max_retries = max_retries
        self.cache = ResponseCache(cache_path, cache_ttl)
        self._sem = asyncio.Semaphore(max_concurrency)
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._host_last: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        self.stats = {"requests": 0, "cached": 0, "errors": 0, "blocked_by_robots": 0}
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": user_agent,
                "Accept-Language": "ru,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            },
            limits=httpx.Limits(max_connections=max_concurrency * 2),
        )

    async def aclose(self) -> None:
        await self._client.aclose()
        self.cache.close()

    async def __aenter__(self) -> "Fetcher":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    # -- вежливость ---------------------------------------------------------

    def _lock(self, host: str) -> asyncio.Lock:
        return self._host_locks.setdefault(host, asyncio.Lock())

    async def _throttle(self, host: str) -> None:
        async with self._lock(host):
            last = self._host_last.get(host, 0.0)
            wait = self.per_host_delay - (time.monotonic() - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._host_last[host] = time.monotonic()

    async def allowed(self, url: str) -> bool:
        """Проверка robots.txt для конкретного URL (результат кэшируется по хосту)."""
        if not self.respect_robots:
            return True
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = await self._load_robots(origin)
        parser = self._robots[origin]
        if parser is None:
            return True  # robots.txt недоступен — считаем, что запрет не установлен
        return parser.can_fetch(self.user_agent, url)

    async def _load_robots(self, origin: str) -> RobotFileParser | None:
        url = f"{origin}/robots.txt"
        try:
            resp = await self._client.get(url)
        except Exception:  # сеть недоступна — не блокируем сбор
            return None
        if resp.status_code >= 400 or not resp.text.strip():
            return None
        parser = RobotFileParser()
        parser.parse(resp.text.splitlines())
        return parser

    # -- запросы ------------------------------------------------------------

    async def get(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        use_cache: bool = True,
        check_robots: bool | None = None,
    ) -> Response | None:
        """GET с кэшем, лимитом частоты и ретраями. None — не удалось получить."""
        if params:
            url = str(httpx.URL(url).copy_merge_params(params))
        if use_cache:
            cached = self.cache.get(url)
            if cached is not None:
                self.stats["cached"] += 1
                return cached

        should_check = self.respect_robots if check_robots is None else check_robots
        if should_check and not await self.allowed(url):
            self.stats["blocked_by_robots"] += 1
            log.info("robots.txt запрещает %s", url)
            return None

        host = urlsplit(url).netloc
        delay = 1.0
        for attempt in range(self.max_retries + 1):
            async with self._sem:
                await self._throttle(host)
                try:
                    self.stats["requests"] += 1
                    resp = await self._client.get(url, headers=headers)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    self.stats["errors"] += 1
                    log.debug("сетевая ошибка %s: %s", url, exc)
                    if attempt >= self.max_retries:
                        return None
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

            if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                retry_after = resp.headers.get("Retry-After")
                pause = float(retry_after) if (retry_after or "").isdigit() else delay
                log.debug("%s → %s, пауза %.1fс", url, resp.status_code, pause)
                await asyncio.sleep(min(pause, 30.0))
                delay *= 2
                continue

            body = resp.text
            if len(body) > self.max_bytes:
                body = body[: self.max_bytes]
            out = Response(str(resp.url), resp.status_code, body, dict(resp.headers))
            if use_cache and out.ok:
                self.cache.put(out)
            return out
        return None

    async def get_json(self, url: str, **kwargs):
        resp = await self.get(url, **kwargs)
        if not resp or not resp.ok:
            return None
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            log.debug("не JSON: %s", url)
            return None

    async def post_json(
        self, url: str, *, data: dict | None = None, json_body: dict | None = None,
        headers: dict | None = None,
    ):
        """POST без кэша — используется API-источниками (DaData и т.п.)."""
        host = urlsplit(url).netloc
        async with self._sem:
            await self._throttle(host)
            try:
                self.stats["requests"] += 1
                resp = await self._client.post(url, data=data, json=json_body, headers=headers)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                self.stats["errors"] += 1
                log.debug("сетевая ошибка POST %s: %s", url, exc)
                return None
        if resp.status_code >= 400:
            log.debug("POST %s → %s", url, resp.status_code)
            return None
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError):
            return None
