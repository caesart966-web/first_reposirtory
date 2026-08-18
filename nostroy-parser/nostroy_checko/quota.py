"""
Суточная квота запросов к checko.ru.

checko.ru даёт ограниченное число бесплатных запросов в сутки (по умолчанию 100)
со сбросом в 00:00. Класс :class:`DailyQuota` — потокобезопасный счётчик,
который:

* атомарно «бронирует» единицу квоты перед запросом (важно при работе
  в несколько потоков — иначе легко проскочить лимит);
* сам сбрасывается при наступлении новых суток по локальному времени;
* умеет сериализоваться в файл состояния, чтобы завтрашний запуск знал,
  сколько запросов уже потрачено сегодня.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date
from typing import Any

from .logging_setup import get_logger

logger = get_logger("quota")


@dataclass(slots=True)
class QuotaSnapshot:
    """Состояние квоты для сохранения в файл."""

    window_date: str        # сутки, к которым относится счётчик (ISO ГГГГ-ММ-ДД)
    used: int               # сколько единиц уже потрачено
    limit: int              # суточный лимит
    exhausted: bool         # сервер явно сообщил, что лимит исчерпан
    exhausted_reason: str   # почему считаем лимит исчерпанным


class QuotaExhausted(RuntimeError):
    """Исключение: суточный лимит запросов исчерпан."""


class DailyQuota:
    """
    Потокобезопасный счётчик суточных запросов.

    Использование::

        quota = DailyQuota(limit=100)
        if quota.reserve():
            try:
                ...  # делаем запрос
            except NetworkErrorBeforeSend:
                quota.release()   # запрос до сервера не дошёл — возвращаем единицу
    """

    def __init__(
        self,
        limit: int = 100,
        used: int = 0,
        window_date: date | None = None,
        exhausted: bool = False,
        exhausted_reason: str = "",
    ) -> None:
        self._lock = threading.Lock()
        self._limit = max(0, int(limit))
        self._used = max(0, int(used))
        self._window_date = window_date or date.today()
        self._exhausted = bool(exhausted)
        self._exhausted_reason = exhausted_reason

    # ----------------------------- свойства ------------------------------- #

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def used(self) -> int:
        with self._lock:
            self._roll_over_if_new_day()
            return self._used

    @property
    def remaining(self) -> int:
        """Сколько запросов осталось до конца суток."""
        with self._lock:
            self._roll_over_if_new_day()
            if self._exhausted:
                return 0
            return max(0, self._limit - self._used)

    @property
    def exhausted(self) -> bool:
        """Исчерпан ли лимит (по счётчику или по ответу сервера)."""
        with self._lock:
            self._roll_over_if_new_day()
            return self._exhausted or self._used >= self._limit

    @property
    def window_date(self) -> date:
        with self._lock:
            self._roll_over_if_new_day()
            return self._window_date

    @property
    def exhausted_reason(self) -> str:
        return self._exhausted_reason

    # ------------------------------ методы -------------------------------- #

    def _roll_over_if_new_day(self) -> None:
        """
        Сбрасывает счётчик при наступлении новых суток.

        Вызывается под уже захваченным замком.
        """
        today = date.today()
        if today != self._window_date:
            logger.info(
                "Наступили новые сутки (%s -> %s): квота сброшена, снова доступно %d запросов",
                self._window_date.isoformat(),
                today.isoformat(),
                self._limit,
            )
            self._window_date = today
            self._used = 0
            self._exhausted = False
            self._exhausted_reason = ""

    def reserve(self, count: int = 1) -> bool:
        """
        Атомарно бронирует ``count`` единиц квоты.

        :return: ``True``, если бронь удалась; ``False``, если лимит исчерпан.
        """
        with self._lock:
            self._roll_over_if_new_day()
            if self._exhausted:
                return False
            if self._used + count > self._limit:
                return False
            self._used += count
            return True

    def release(self, count: int = 1) -> None:
        """
        Возвращает ранее забронированные единицы.

        Вызывается, только если запрос гарантированно не дошёл до сервера
        (ошибка DNS, отказ в соединении) — в этом случае checko его не учёл.
        """
        with self._lock:
            self._used = max(0, self._used - count)

    def mark_exhausted(self, reason: str = "") -> None:
        """
        Помечает лимит исчерпанным принудительно.

        Вызывается при получении HTTP 429 или страницы «лимит запросов
        исчерпан»: сервер знает лучше нашего счётчика.
        """
        with self._lock:
            if not self._exhausted:
                logger.warning("Суточный лимит checko.ru исчерпан: %s", reason or "ответ сервера")
            self._exhausted = True
            self._exhausted_reason = reason
            self._used = max(self._used, self._limit)

    def progress_line(self) -> str:
        """Строка прогресса для вывода оператору."""
        with self._lock:
            self._roll_over_if_new_day()
            remaining = 0 if self._exhausted else max(0, self._limit - self._used)
            return (
                f"квота checko.ru на {self._window_date.isoformat()}: "
                f"использовано {self._used}/{self._limit}, осталось {remaining}"
            )

    # --------------------------- сериализация ------------------------------ #

    def snapshot(self) -> QuotaSnapshot:
        with self._lock:
            return QuotaSnapshot(
                window_date=self._window_date.isoformat(),
                used=self._used,
                limit=self._limit,
                exhausted=self._exhausted,
                exhausted_reason=self._exhausted_reason,
            )

    def to_dict(self) -> dict[str, Any]:
        snapshot = self.snapshot()
        return {
            "window_date": snapshot.window_date,
            "used": snapshot.used,
            "limit": snapshot.limit,
            "exhausted": snapshot.exhausted,
            "exhausted_reason": snapshot.exhausted_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None, limit: int | None = None) -> "DailyQuota":
        """
        Восстанавливает квоту из файла состояния.

        Если в файле записаны вчерашние сутки — счётчик автоматически
        обнулится при первом обращении (новый день = новые 100 запросов).
        """
        if not data:
            return cls(limit=limit if limit is not None else 100)
        try:
            window_date = date.fromisoformat(str(data.get("window_date", "")))
        except ValueError:
            window_date = date.today()
        stored_limit = int(data.get("limit", 100) or 100)
        return cls(
            limit=limit if limit is not None else stored_limit,
            used=int(data.get("used", 0) or 0),
            window_date=window_date,
            exhausted=bool(data.get("exhausted", False)),
            exhausted_reason=str(data.get("exhausted_reason", "")),
        )
