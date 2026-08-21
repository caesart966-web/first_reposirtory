"""Настройки обращения к открытым реестрам.

Реестры НОСТРОЙ и НОПРИЗ бесплатны и ключей не требуют, поэтому настраивать
здесь почти нечего — вежливая частота запросов, таймаут и прокси.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    #: Запросов в секунду. Реестр — общий публичный ресурс, не частим.
    nostroy_rps: float = 1.0
    #: Таймаут одного запроса, секунды.
    timeout: float = 30.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    #: Адрес прокси, если прямой выход в сеть закрыт.
    proxy: str = ""
    #: Куда складывать образец ответа реестра и логи.
    sample_dir: str = "output"

    def proxies(self) -> dict[str, str] | None:
        """Словарь прокси для requests (или None, если прокси не задан)."""
        if self.proxy:
            return {"http": self.proxy, "https": self.proxy}
        # Уважаем системные переменные окружения, если они заданы.
        env_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if env_proxy:
            return {"http": env_proxy, "https": env_proxy}
        return None
