"""Утилиты: конфиг, логирование, нормализация ИНН, ретраи, HTTP-сессия."""
from __future__ import annotations

import logging
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests
import yaml
from dotenv import load_dotenv
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("sro_leads")


# ----------------------------------------------------------------------------
# Конфиг
# ----------------------------------------------------------------------------
def load_config(path: Optional[str | Path] = None) -> dict[str, Any]:
    load_dotenv(PROJECT_ROOT / ".env")
    cfg_path = Path(path or os.environ.get("SRO_LEADS_CONFIG") or PROJECT_ROOT / "config.yaml")
    if not cfg_path.is_absolute():
        cfg_path = PROJECT_ROOT / cfg_path
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg.setdefault("paths", {})
    cfg["_root"] = str(PROJECT_ROOT)
    return cfg


def resolve_path(cfg: dict[str, Any], key: str, default: str = "") -> Path:
    """Путь из блока paths относительно корня проекта; папка создаётся."""
    raw = cfg.get("paths", {}).get(key, default)
    p = Path(raw)
    if not p.is_absolute():
        p = Path(cfg.get("_root", PROJECT_ROOT)) / p
    if p.suffix:
        p.parent.mkdir(parents=True, exist_ok=True)
    else:
        p.mkdir(parents=True, exist_ok=True)
    return p


# ----------------------------------------------------------------------------
# Логирование: logs/YYYY-MM-DD.log + консоль, уровень INFO
# ----------------------------------------------------------------------------
def setup_logging(logs_dir: Path, level: int = logging.INFO) -> logging.Logger:
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("sro_leads")
    logger.setLevel(level)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    fh = logging.FileHandler(logs_dir / f"{today_str()}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    try:  # Windows-консоль: не падать на кириллице
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


# ----------------------------------------------------------------------------
# Даты
# ----------------------------------------------------------------------------
def today_str() -> str:
    return date.today().isoformat()


def now_str() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def parse_date(value: Any) -> Optional[str]:
    """Дата из Excel/строки в YYYY-MM-DD. Не распозналась — None."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = str(value).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        y, mo, d = m.groups()
    else:
        m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", s)
        if not m:
            return None
        d, mo, y = m.groups()
        if len(y) == 2:
            y = "20" + y
    try:
        return date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return None


def days_between(d1: str, d2: str) -> int:
    return (date.fromisoformat(d2) - date.fromisoformat(d1)).days


def days_ago(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


# ----------------------------------------------------------------------------
# ИНН: всегда строка, 10 знаков у юрлиц, 12 у ИП, ведущие нули значимы.
# ----------------------------------------------------------------------------
_INN_DIGITS = re.compile(r"\D+")


def normalize_inn(value: Any) -> Optional[str]:
    """Приводит ИНН к строке из 10 или 12 цифр. Мусор -> None.

    Excel/pandas могут отдать число (7814858513.0) — тогда ведущий ноль уже потерян:
    9 или 11 цифр дополняем нулём слева.
    """
    if value is None:
        return None
    if isinstance(value, float):
        if value != value:  # NaN
            return None
        value = int(value)
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".")[0]
    if re.fullmatch(r"\d\.\d+e\+?\d+", s.lower()):
        try:
            s = str(int(float(s)))
        except ValueError:
            return None
    digits = _INN_DIGITS.sub("", s)
    if len(digits) in (9, 11):
        digits = "0" + digits
    if len(digits) not in (10, 12):
        return None
    return digits


def inn_checksum_ok(inn: str) -> bool:
    """Контрольные цифры ИНН (справочно; в пайплайне не блокирует)."""
    def ctrl(digits: str, weights: list[int]) -> int:
        return sum(int(d) * w for d, w in zip(digits, weights)) % 11 % 10

    if len(inn) == 10:
        return ctrl(inn[:9], [2, 4, 10, 3, 5, 9, 4, 6, 8]) == int(inn[9])
    if len(inn) == 12:
        w11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        w12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        return ctrl(inn[:10], w11) == int(inn[10]) and ctrl(inn[:11], w12) == int(inn[11])
    return False


# ----------------------------------------------------------------------------
# Вложенные поля JSON: "data.data" -> obj["data"]["data"]; список путей = варианты
# ----------------------------------------------------------------------------
def dig(obj: Any, path: str | list[str] | None, default: Any = None) -> Any:
    if path is None:
        return default
    paths = [path] if isinstance(path, str) else list(path)
    for p in paths:
        cur = obj
        ok = True
        for part in p.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
            else:
                ok = False
                break
        if ok and cur is not None:
            return cur
    return default


def clean_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


# ----------------------------------------------------------------------------
# HTTP: таймаут, ретраи с экспоненциальной паузой, вежливая пауза по домену
# ----------------------------------------------------------------------------
class RetryableHTTPError(Exception):
    pass


class HttpClient:
    """Тонкая обёртка над requests.Session с ретраями и паузой между запросами к домену."""

    def __init__(self, http_cfg: dict[str, Any] | None = None):
        http_cfg = http_cfg or {}
        self.timeout = float(http_cfg.get("timeout", 10))
        self.retries = int(http_cfg.get("retries", 3))
        self.backoff_base = float(http_cfg.get("backoff_base", 2))
        self.domain_delay = float(http_cfg.get("domain_delay", 1.0))
        self.session = requests.Session()
        self.session.headers["User-Agent"] = http_cfg.get("user_agent", "sro-leads/1.0")
        self._last_hit: dict[str, float] = {}

    def _polite_wait(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_hit.get(host)
        if last is not None:
            wait = self.domain_delay - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_hit[host] = time.monotonic()

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        attempts = max(1, self.retries)

        @retry(
            reraise=True,
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=self.backoff_base, min=self.backoff_base, max=60),
            retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout, RetryableHTTPError)),
            before_sleep=before_sleep_log(log, logging.WARNING),
        )
        def _do() -> requests.Response:
            self._polite_wait(url)
            kwargs.setdefault("timeout", self.timeout)
            resp = self.session.request(method, url, **kwargs)
            if resp.status_code >= 500 or resp.status_code == 429:
                raise RetryableHTTPError(f"{resp.status_code} {url}")
            return resp

        return _do()

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", url, **kwargs)


def domain_of(url: str) -> str:
    host = urlparse(url if "://" in url else "http://" + url).netloc.lower()
    return host[4:] if host.startswith("www.") else host
