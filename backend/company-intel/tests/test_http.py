import time
from urllib.robotparser import RobotFileParser

import pytest

from company_intel.http import Fetcher, Response, ResponseCache


def test_cache_roundtrip(tmp_path):
    cache = ResponseCache(tmp_path / "c.sqlite3", ttl_seconds=60)
    cache.put(Response("https://x.ru/", 200, "<html>ok</html>", {"a": "b"}))
    hit = cache.get("https://x.ru/")
    assert hit is not None and hit.from_cache and hit.text == "<html>ok</html>"
    assert cache.get("https://x.ru/other") is None
    cache.close()


def test_cache_expires(tmp_path):
    cache = ResponseCache(tmp_path / "c.sqlite3", ttl_seconds=0)
    cache.put(Response("https://x.ru/", 200, "old", {}))
    time.sleep(0.01)
    assert cache.get("https://x.ru/") is None
    cache.close()


def test_cache_disabled_is_noop():
    cache = ResponseCache(None)
    cache.put(Response("https://x.ru/", 200, "body", {}))
    assert cache.get("https://x.ru/") is None


async def test_robots_rules_are_respected():
    fetcher = Fetcher(cache_path=None, respect_robots=True)
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /private"])
    fetcher._robots["https://x.ru"] = parser
    try:
        assert await fetcher.allowed("https://x.ru/contacts")
        assert not await fetcher.allowed("https://x.ru/private/data")
    finally:
        await fetcher.aclose()


async def test_robots_can_be_switched_off():
    fetcher = Fetcher(cache_path=None, respect_robots=False)
    parser = RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /"])
    fetcher._robots["https://x.ru"] = parser
    try:
        assert await fetcher.allowed("https://x.ru/private")
    finally:
        await fetcher.aclose()


def test_response_helpers():
    resp = Response("https://x.ru/", 200, '{"a": 1}', {})
    assert resp.ok and resp.json() == {"a": 1}
    assert not Response("https://x.ru/", 404, "", {}).ok
