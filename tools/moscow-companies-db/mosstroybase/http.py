"""Общая HTTP-сессия с повторами и таймаутами."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import USER_AGENT

DEFAULT_TIMEOUT = 30


def make_session(user_agent: str | None = None, retries: bool = True) -> requests.Session:
    """HTTP-сессия; retries=False — для обхода сайтов компаний, где повторные
    попытки на мёртвых доменах только затягивают прогон."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
    ) if retries else Retry(total=0)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers["User-Agent"] = user_agent or USER_AGENT
    return session
