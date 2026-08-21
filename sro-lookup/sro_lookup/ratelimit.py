"""Ограничитель частоты обращений к реестру."""

from __future__ import annotations

import threading
import time


class RateLimiter:
    """Общий на все потоки ограничитель частоты запросов.

    Реестры НОСТРОЙ и НОПРИЗ — общие публичные ресурсы без объявленных
    лимитов. Соблюдаем минимальный интервал между обращениями независимо
    от числа рабочих потоков: вежливость к чужому серверу.
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
