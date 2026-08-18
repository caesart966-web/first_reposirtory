"""Поддельный HTTP-клиент для тестов: отдаёт заранее заданные ответы без сети."""
from __future__ import annotations

import json

from company_intel.http import Response


class FakeFetcher:
    """Совместим по интерфейсу с `company_intel.http.Fetcher`."""

    def __init__(self, routes: dict[str, str], json_routes: dict | None = None) -> None:
        self.routes = routes
        self.json_routes = json_routes or {}
        self.stats = {"requests": 0, "cached": 0, "errors": 0, "blocked_by_robots": 0}
        self.seen: list[str] = []

    async def get(self, url: str, *, params=None, headers=None, use_cache=True,
                  check_robots=None) -> Response | None:
        self.seen.append(url)
        self.stats["requests"] += 1
        body = self.routes.get(url)
        if body is None:
            return Response(url, 404, "", {})
        return Response(url, 200, body, {"content-type": "text/html"})

    async def get_json(self, url: str, **kwargs):
        self.seen.append(url)
        self.stats["requests"] += 1
        data = self.json_routes.get(url)
        return json.loads(json.dumps(data)) if data is not None else None

    async def post_json(self, url: str, *, data=None, json_body=None, headers=None):
        self.seen.append(url)
        self.stats["requests"] += 1
        return self.json_routes.get(url)

    async def aclose(self) -> None:
        return None
