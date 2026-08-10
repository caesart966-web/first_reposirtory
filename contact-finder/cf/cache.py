"""Кэш ответов на диске (SQLite).

Зачем: у платных API лимит запросов в сутки. Повторный запуск программы не
должен жечь квоту заново — если по ИНН уже ходили, ответ берётся из кэша.
Кэш также спасает, если прогон оборвался на середине списка.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / ".cache" / "responses.sqlite"


class Cache:
    def __init__(self, path: Path | str | None = None, ttl_days: int = 30) -> None:
        self.path = Path(path or DEFAULT_PATH)
        self.ttl = ttl_days * 86400
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS responses ("
            " key TEXT PRIMARY KEY, body TEXT, created REAL)"
        )
        self._conn.commit()

    def get(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT body, created FROM responses WHERE key = ?", (key,)
        ).fetchone()
        if not row:
            return None
        body, created = row
        if self.ttl and (time.time() - created) > self.ttl:
            return None
        return body

    def put(self, key: str, body: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO responses (key, body, created) VALUES (?, ?, ?)",
            (key, body, time.time()),
        )
        self._conn.commit()

    def stats(self) -> tuple[int, str]:
        count = self._conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        return count, str(self.path)

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:  # noqa: BLE001
            pass


# Общий экземпляр на процесс — источники берут его отсюда.
_shared: Cache | None = None


def shared() -> Cache:
    global _shared
    if _shared is None:
        _shared = Cache()
    return _shared
