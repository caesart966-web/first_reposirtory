"""Загрузка конфигурации: config.yaml + переменные окружения (.env).

Все ключи API живут только в .env / окружении — в коде и в config.yaml их нет.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

# Значения по умолчанию — используются, если ключа нет в config.yaml
DEFAULTS: dict[str, Any] = {
    "app": {
        "contact_email": "owner@example.com",
        "user_agent": "ContactFinderBot/1.0",
    },
    "http": {
        "concurrency": 10,
        "per_host_rps": 5.0,
        "connect_timeout": 10,
        "read_timeout": 30,
        "retries": 5,
        "backoff": [2, 4, 8, 16, 32],
        "respect_robots": True,
        "proxy_check_url": "https://api.ipify.org",
    },
    "cache": {
        "ttl_days": 30,
        "db_path": "data/finder.db",
    },
    "depth": "full",
    "sources": {},
    "circuit_breaker": {
        "error_threshold": 5,
        "pause_minutes": 15,
    },
    "validation": {
        "check_mx": True,
        "email_stop_prefixes": [],
        "email_stop_addresses": [],
        "dev_stoplist_domains": [],
        "free_mail_domains": [],
        "aggregator_domains": [],
    },
    "scoring": {
        "level_a": 40,
        "verified_site": 30,
        "multi_source": 15,
        "corp_domain": 10,
        "level_d_unverified": -20,
        "liquidated": -30,
        "base_b_unverified": 15,
        "base_c": 20,
    },
    "output": {
        "logs_dir": "logs",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    """Обёртка над словарём конфигурации с доступом по пути «a.b.c»."""

    def __init__(self, data: dict[str, Any], base_dir: Path):
        self.data = data
        self.base_dir = base_dir

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
        base_dir = cfg_path.resolve().parent
        # .env ищем рядом с конфигом и в текущем каталоге
        load_dotenv(base_dir / ".env")
        load_dotenv()
        data: dict[str, Any] = {}
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        return cls(_deep_merge(DEFAULTS, data), base_dir)

    def get(self, path: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in path.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def resolve_path(self, path_str: str) -> Path:
        """Относительные пути в конфиге считаем от каталога проекта."""
        p = Path(path_str)
        return p if p.is_absolute() else self.base_dir / p

    # --- часто используемые значения -------------------------------------

    @property
    def user_agent(self) -> str:
        email = self.env("CONTACT_EMAIL") or self.get("app.contact_email")
        return f"{self.get('app.user_agent')} (+mailto:{email})"

    @property
    def db_path(self) -> Path:
        return self.resolve_path(self.get("cache.db_path"))

    @property
    def cache_ttl_seconds(self) -> int:
        return int(self.get("cache.ttl_days", 30)) * 86400

    @property
    def backoff_delays(self) -> list[float]:
        return [float(x) for x in self.get("http.backoff", [2, 4, 8, 16, 32])]

    def source_cfg(self, name: str) -> dict[str, Any]:
        return self.get(f"sources.{name}", {}) or {}

    def source_enabled(self, name: str) -> bool:
        return bool(self.source_cfg(name).get("enabled", True))

    def source_priority(self, name: str, fallback: int) -> int:
        return int(self.source_cfg(name).get("priority", fallback))

    @staticmethod
    def env(name: str, default: Optional[str] = None) -> Optional[str]:
        """Ключи API и секреты — только из окружения."""
        value = os.environ.get(name, default)
        return value.strip() if isinstance(value, str) else value

    def proxy_pool(self) -> list[str]:
        raw = self.env("HTTP_PROXY_POOL", "") or ""
        return [p.strip() for p in raw.split(",") if p.strip()]
