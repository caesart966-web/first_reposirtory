"""Конфигурация запуска. Значения берутся из CLI-аргументов и окружения."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    delay: float = 1.5          # пауза между запросами к одному хосту, сек
    timeout: float = 25.0       # таймаут запроса, сек
    retries: int = 3            # число попыток на запрос
    max_sites: int = 3          # сколько доменов-кандидатов проверять на сайт
    proxy: str | None = None    # http(s)-прокси, если нужен
    verbose: bool = False

    # Ключи внешних API — необязательные, повышают полноту.
    dgis_key: str | None = None            # 2ГИС Catalog API
    yandex_user: str | None = None         # Яндекс XML search
    yandex_key: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            proxy=os.environ.get("CF_PROXY") or None,
            dgis_key=os.environ.get("DGIS_API_KEY") or None,
            yandex_user=os.environ.get("YANDEX_XML_USER") or None,
            yandex_key=os.environ.get("YANDEX_XML_KEY") or None,
        )
