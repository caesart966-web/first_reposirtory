"""
Сохранение прогресса между запусками.

Это ключевой модуль для работы «по дням»: checko.ru отдаёт лишь 100 бесплатных
запросов в сутки, поэтому обработка большого реестра растягивается на несколько
дней. Файл состояния ``output/state/checko_state.json`` хранит:

* счётчик суточной квоты и дату, к которой он относится;
* все уже полученные с checko.ru данные (ключ -> контакты);
* историю неудачных попыток (чтобы не долбиться бесконечно в одну компанию);
* очередь: какие ключи ещё не обработаны.

Запись выполняется атомарно (во временный файл + ``os.replace``), поэтому
прерывание скрипта на середине не портит уже собранные данные.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .logging_setup import get_logger
from .models import CheckoContacts, utcnow_iso
from .quota import DailyQuota

logger = get_logger("state")

#: Версия формата файла состояния (на случай будущих изменений структуры).
STATE_VERSION = 1

#: Минимальный интервал между автосохранениями, секунды.
_AUTOSAVE_INTERVAL = 5.0


@dataclass(slots=True)
class AttemptInfo:
    """История попыток запросить одну компанию."""

    count: int = 0
    last_status: str = ""
    last_error: str = ""
    last_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "last_time": self.last_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttemptInfo":
        return cls(
            count=int(data.get("count", 0) or 0),
            last_status=data.get("last_status", ""),
            last_error=data.get("last_error", ""),
            last_time=data.get("last_time", ""),
        )


class StateStore:
    """
    Файл состояния: квота + собранные данные + история попыток.

    Потокобезопасен: методы можно вызывать из рабочих потоков
    :class:`concurrent.futures.ThreadPoolExecutor`.
    """

    def __init__(self, path: Path, daily_limit: int = 100) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._results: dict[str, CheckoContacts] = {}
        self._nostroy: dict[str, dict] = {}      # кэш ответов реестра НОСТРОЙ (по ИНН)
        self._attempts: dict[str, AttemptInfo] = {}
        self._meta: dict[str, Any] = {}
        self.quota = DailyQuota(limit=daily_limit)
        self._dirty = False
        self._last_save = 0.0
        self._daily_limit = daily_limit

    # ------------------------------ загрузка ------------------------------- #

    def load(self) -> None:
        """
        Читает файл состояния, если он есть.

        Битый файл не считается фатальной ошибкой: он переименовывается
        в ``*.corrupted`` и работа начинается с чистого состояния — терять
        уже собранное неприятно, но остановить весь процесс хуже.
        """
        with self._lock:
            if not self.path.exists():
                logger.info("Файл состояния не найден — начинаем с чистого листа: %s", self.path)
                self.quota = DailyQuota(limit=self._daily_limit)
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.error("Файл состояния повреждён (%s) — создаём новый", exc)
                self._backup_corrupted()
                self.quota = DailyQuota(limit=self._daily_limit)
                return

            self.quota = DailyQuota.from_dict(raw.get("quota"), limit=self._daily_limit)
            self._results = {
                key: CheckoContacts.from_dict(value)
                for key, value in (raw.get("results") or {}).items()
            }
            self._attempts = {
                key: AttemptInfo.from_dict(value)
                for key, value in (raw.get("attempts") or {}).items()
            }
            self._meta = dict(raw.get("meta") or {})
            self._nostroy = dict(raw.get("nostroy") or {})
            logger.info(
                "Состояние загружено: результатов %d, неудачных попыток %d, %s",
                len(self._results),
                len(self._attempts),
                self.quota.progress_line(),
            )

    def _backup_corrupted(self) -> None:
        """Отводит повреждённый файл в сторону, чтобы не потерять его совсем."""
        try:
            backup = self.path.with_suffix(f".corrupted-{int(time.time())}.json")
            shutil.move(str(self.path), str(backup))
            logger.warning("Повреждённый файл состояния сохранён как %s", backup)
        except OSError as exc:
            logger.error("Не удалось сохранить копию повреждённого состояния: %s", exc)

    def reset(self) -> None:
        """Полностью очищает состояние (ключ ``--reset-state``)."""
        with self._lock:
            self._results.clear()
            self._attempts.clear()
            self._nostroy.clear()
            self._meta.clear()
            self.quota = DailyQuota(limit=self._daily_limit)
            self._dirty = True
            logger.warning("Состояние сброшено по требованию пользователя")

    # ------------------------------ доступ --------------------------------- #

    def get_result(self, key: str) -> CheckoContacts | None:
        """Ранее полученный результат по ключу компании."""
        with self._lock:
            return self._results.get(key)

    def has_final_result(self, key: str) -> bool:
        """Есть ли по компании окончательный результат (``ok`` или ``not_found``)."""
        with self._lock:
            result = self._results.get(key)
            return bool(result and result.is_final)

    def all_results(self) -> dict[str, CheckoContacts]:
        with self._lock:
            return dict(self._results)

    def set_result(self, key: str, result: CheckoContacts) -> None:
        """Сохраняет результат запроса и обновляет историю попыток."""
        with self._lock:
            previous = self._results.get(key)
            # Успешный результат никогда не затирается неуспешным:
            # данные, добытые ценой квоты, слишком дороги.
            if previous and previous.is_final and not result.is_final:
                logger.debug("Результат по %s не перезаписан (был %s, стал %s)",
                             key, previous.status, result.status)
            else:
                self._results[key] = result

            attempt = self._attempts.get(key) or AttemptInfo()
            attempt.count += 1
            attempt.last_status = result.status
            attempt.last_error = result.error
            attempt.last_time = utcnow_iso()
            self._attempts[key] = attempt
            self._dirty = True

    def normalize_addresses(self) -> dict[str, int]:
        """Оставляет в каждой карточке один адрес — юридический.

        Карточки, полученные до исправления разбора, хранят весь список:
        юридический адрес, адреса подразделений и адрес самой СРО. Пересборка
        идёт по уже сохранённым данным — без запросов к checko.ru и без
        расхода квоты, поэтому уже пробитые компании остаются пробитыми.

        Возвращает счётчики для лога. Повторный вызов ничего не меняет.
        """
        from .address_pick import detect_shared_addresses, full_address_list, rebuild_card

        with self._lock:
            cards = list(self._results.items())
            shared = detect_shared_addresses(
                full_address_list(card.addresses, card.extra) for _, card in cards
            )
            stats = {"changed": 0, "ambiguous": 0, "empty": 0, "shared": len(shared)}
            for key, card in cards:
                addresses, extra, ambiguous, empty = rebuild_card(
                    card.addresses, card.extra, card.inn or key, shared
                )
                if addresses == card.addresses:
                    continue
                card.addresses = addresses
                card.extra = extra
                stats["changed"] += 1
                stats["ambiguous"] += int(ambiguous)
                stats["empty"] += int(empty)
            if stats["changed"]:
                self._dirty = True
            return stats

    def get_attempts(self, key: str) -> AttemptInfo:
        with self._lock:
            return self._attempts.get(key) or AttemptInfo()

    def get_nostroy(self, inn: str) -> dict | None:
        """Кэшированный ответ реестра НОСТРОЙ по ИНН (или None)."""
        with self._lock:
            return self._nostroy.get(inn)

    def set_nostroy(self, inn: str, payload: dict) -> None:
        """Кладёт ответ реестра НОСТРОЙ в кэш — реестр не дёргается повторно."""
        with self._lock:
            self._nostroy[inn] = payload
            self._dirty = True

    def set_meta(self, **values: Any) -> None:
        """Сохраняет произвольные служебные сведения о запуске."""
        with self._lock:
            self._meta.update(values)
            self._dirty = True

    @property
    def meta(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._meta)

    # ------------------------------ сохранение ----------------------------- #

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "version": STATE_VERSION,
                "updated_at": utcnow_iso(),
                "quota": self.quota.to_dict(),
                "results": {key: value.to_dict() for key, value in self._results.items()},
                "attempts": {key: value.to_dict() for key, value in self._attempts.items()},
                "nostroy": self._nostroy,
                "meta": self._meta,
            }

    def save(self, force: bool = True) -> None:
        """
        Атомарно записывает состояние на диск.

        :param force: если ``False``, запись выполняется не чаще, чем раз
                      в :data:`_AUTOSAVE_INTERVAL` секунд (автосохранение
                      в процессе работы).
        """
        with self._lock:
            now = time.monotonic()
            if not force:
                if not self._dirty or (now - self._last_save) < _AUTOSAVE_INTERVAL:
                    return
            payload = self.to_dict()
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".json.tmp")
            try:
                temporary.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                os.replace(temporary, self.path)     # атомарная подмена файла
                self._dirty = False
                self._last_save = now
            except OSError as exc:
                logger.error("Не удалось сохранить состояние в %s: %s", self.path, exc)
            finally:
                if temporary.exists():
                    try:
                        temporary.unlink()
                    except OSError:
                        pass

    # ------------------------------ статистика ----------------------------- #

    def summary(self) -> dict[str, int]:
        """Сводка по накопленным результатам — для лога и отчёта."""
        with self._lock:
            counters: dict[str, int] = {}
            for result in self._results.values():
                counters[result.status] = counters.get(result.status, 0) + 1
            counters["total"] = len(self._results)
            return counters
