"""Конфигурация прогона: ключи API, лимиты, включённые источники.

Ключи берутся из переменных окружения или файла `.env` рядом с проектом.
В репозиторий ключи не попадают — `.env` в `.gitignore`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Имя переменной окружения → зачем нужна.
KEY_HELP = {
    "DADATA_TOKEN": "DaData: реквизиты по ИНН/названию (бесплатно до 10 000 запросов/сут)",
    "DADATA_SECRET": "DaData: секретный ключ (нужен только для /clean, не для suggestions)",
    "CHECKO_KEY": "Checko.ru: карточка компании, связи, финансы",
    "HUNTER_API_KEY": "Hunter.io: корпоративные адреса по домену",
    "SERPAPI_KEY": "SerpApi: выдача Google/Yandex через API",
    "GOOGLE_CSE_KEY": "Google Programmable Search: ключ API",
    "GOOGLE_CSE_CX": "Google Programmable Search: идентификатор поисковой системы",
    "YANDEX_XML_USER": "Яндекс XML: логин",
    "YANDEX_XML_KEY": "Яндекс XML: ключ",
    "BRAVE_API_KEY": "Brave Search API: ключ",
    "TWOGIS_KEY": "2ГИС Catalog API: карточка организации в справочнике",
}


def load_dotenv(path: str | Path | None = None) -> dict[str, str]:
    """Простейший разбор .env (KEY=VALUE, # — комментарий). Не перетирает окружение."""
    candidates = [Path(path)] if path else [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    loaded: dict[str, str] = {}
    for file in candidates:
        if not file.is_file():
            continue
        for line in file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            loaded[key] = value
            os.environ.setdefault(key, value)
        break
    return loaded


@dataclass
class Config:
    """Настройки прогона."""
    keys: dict[str, str] = field(default_factory=dict)
    per_host_delay: float = 1.0
    max_concurrency: int = 8
    timeout: float = 20.0
    respect_robots: bool = True
    cache_path: str | None = ".cache/http.sqlite3"
    cache_ttl: int = 86_400
    max_pages_per_site: int = 12
    max_search_results: int = 20
    max_rounds: int = 3
    country: str = "ru"
    enabled_sources: list[str] | None = None    # None — все доступные
    disabled_sources: list[str] = field(default_factory=list)
    allow_email_guessing: bool = False          # гипотезы адресов по шаблону
    fetch_search_results: bool = True           # заходить на страницы из выдачи

    @classmethod
    def from_env(cls, **overrides) -> "Config":
        load_dotenv()
        keys = {name: os.environ[name] for name in KEY_HELP if os.environ.get(name)}
        return cls(keys=keys, **overrides)

    def key(self, name: str) -> str | None:
        return self.keys.get(name) or os.environ.get(name) or None

    def has(self, *names: str) -> bool:
        return all(self.key(n) for n in names)

    def is_enabled(self, source_name: str) -> bool:
        if source_name in self.disabled_sources:
            return False
        if self.enabled_sources is None:
            return True
        return source_name in self.enabled_sources
