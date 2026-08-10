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
import urllib.request
import zlib

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
        for attempt in range(1, self.retries + 1):
            self._throttle()
            try:
                if self._session is not None:
                    return self._get_requests(url)
                return self._get_urllib(url)
            except Exception as exc:  # noqa: BLE001
                if self.verbose:
                    print(f"    ! попытка {attempt}/{self.retries} {url} — {exc}")
                if attempt < self.retries:
                    time.sleep(2 ** attempt)
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
