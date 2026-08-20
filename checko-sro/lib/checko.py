"""Клиент api.checko.ru: кэш на диске и жёсткий суточный лимит запросов.

Лимит тарифа — 100 запросов в сутки, поэтому клиент:
  * никогда не ходит в сеть за ИНН, который уже лежит в кэше;
  * считает израсходованные за сегодня запросы и останавливается сам.
Так повторный запуск скрипта не тратит ни одного запроса впустую.
"""
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

API_BASE = "https://api.checko.ru/v2"
DAILY_LIMIT = 100
# Пауза между запросами: Чеко ограничивает не только сутки, но и частоту.
REQUEST_PAUSE_SECONDS = 1.0


class QuotaExhausted(Exception):
    """Суточный лимит исчерпан — остальные ИНН ждут следующего дня."""


class CheckoClient:
    def __init__(self, api_key, cache_dir, daily_limit=DAILY_LIMIT):
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.daily_limit = daily_limit
        self.quota_path = self.cache_dir / "_quota.json"
        self.requests_made = 0

    # --- кэш -------------------------------------------------------------
    def _cache_path(self, inn):
        return self.cache_dir / f"{inn}.json"

    def cached(self, inn):
        path = self._cache_path(inn)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _store(self, inn, payload):
        self._cache_path(inn).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # --- суточная квота --------------------------------------------------
    def _quota_state(self):
        today = date.today().isoformat()
        if self.quota_path.exists():
            state = json.loads(self.quota_path.read_text(encoding="utf-8"))
            if state.get("date") == today:
                return state
        return {"date": today, "used": 0}

    def quota_left(self):
        return max(0, self.daily_limit - self._quota_state()["used"])

    def _consume_quota(self):
        state = self._quota_state()
        state["used"] += 1
        self.quota_path.write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )

    # --- сеть ------------------------------------------------------------
    def _endpoint(self, inn):
        """12 цифр — ИП (ЕГРИП), 10 — юрлицо (ЕГРЮЛ): у них разные ручки."""
        return "entrepreneur" if len(str(inn)) == 12 else "company"

    def fetch(self, inn, force=False):
        """Возвращает сырой ответ Чеко. Из кэша, если он есть."""
        inn = str(inn).strip()
        if not force:
            cached = self.cached(inn)
            if cached is not None:
                return cached

        if self.quota_left() <= 0:
            raise QuotaExhausted(
                f"израсходованы все {self.daily_limit} запросов за сегодня"
            )

        params = urllib.parse.urlencode({"key": self.api_key, "inn": inn})
        url = f"{API_BASE}/{self._endpoint(inn)}?{params}"

        self._consume_quota()
        self.requests_made += 1
        request = urllib.request.Request(url, headers={"User-Agent": "sro-report/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))

        payload["_fetched_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        payload["_endpoint"] = self._endpoint(inn)
        self._store(inn, payload)
        time.sleep(REQUEST_PAUSE_SECONDS)
        return payload


# --- разбор ответа -------------------------------------------------------
# Чеко отдаёт разную структуру для ЕГРЮЛ и ЕГРИП, и часть полей может
# отсутствовать. Все геттеры ниже переживают отсутствие любого ключа.

def _first_dict(value):
    """Руковод приходит то словарём, то списком словарей."""
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value:
        return value[0] if isinstance(value[0], dict) else {}
    return {}


def _as_list(value):
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value).strip()]


def extract(payload):
    """Сырой ответ -> плоский словарь полей отчёта."""
    if not payload or not isinstance(payload, dict):
        return {}
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        return {}

    address = None
    for key in ("ЮрАдрес", "Адрес"):
        node = data.get(key)
        if isinstance(node, dict):
            address = node.get("АдресРФ") or node.get("Адрес")
        elif isinstance(node, str):
            address = node
        if address:
            break

    head = _first_dict(data.get("Руковод"))
    director = head.get("ФИО") or head.get("Фио") or data.get("ФИО")

    contacts = data.get("Контакты") or {}
    if not isinstance(contacts, dict):
        contacts = {}
    phones = _as_list(contacts.get("Тел")) or _as_list(data.get("Тел"))
    emails = _as_list(contacts.get("Емэйл")) or _as_list(data.get("Емэйл"))

    status = data.get("Статус")
    if isinstance(status, dict):
        status = status.get("Наим")

    return {
        "name_full": data.get("НаимПолн") or data.get("НаимСокр") or data.get("ФИО"),
        "name_short": data.get("НаимСокр"),
        "address": (address or "").strip() or None,
        "director": (director or "").strip() or None,
        "phones": phones,
        "emails": emails,
        "egrul_status": status,
    }
