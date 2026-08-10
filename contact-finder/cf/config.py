"""Конфигурация запуска. Значения берутся из CLI-аргументов, .env и окружения."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Читает файл .env рядом с программой: КЛЮЧ=значение, # — комментарий.

    Так ключи не приходится каждый раз вбивать в командную строку и они не
    попадают в историю терминала.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class Config:
    delay: float = 1.5          # пауза между запросами к одному хосту, сек
    timeout: float = 25.0       # таймаут запроса, сек
    retries: int = 3            # число попыток на запрос
    max_sites: int = 3          # сколько доменов-кандидатов проверять на сайт
    proxy: str | None = None    # http(s)-прокси, если нужен
    verbose: bool = False
    no_cache: bool = False      # не использовать кэш ответов (жжёт квоту API)

    # Ключи внешних API — необязательные, повышают полноту.
    checko_key: str | None = None          # api.checko.ru — структурные контакты
    datanewton_key: str | None = None      # api.datanewton.ru
    dgis_key: str | None = None            # 2ГИС Catalog API
    yandex_user: str | None = None         # Яндекс XML search
    yandex_key: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        _load_dotenv()
        return cls(
            proxy=os.environ.get("CF_PROXY") or None,
            checko_key=os.environ.get("CHECKO_API_KEY") or None,
            datanewton_key=os.environ.get("DATANEWTON_API_KEY") or None,
            dgis_key=os.environ.get("DGIS_API_KEY") or None,
            yandex_user=os.environ.get("YANDEX_XML_USER") or None,
            yandex_key=os.environ.get("YANDEX_XML_KEY") or None,
        )
