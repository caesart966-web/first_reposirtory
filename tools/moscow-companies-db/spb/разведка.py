"""Разведка API реестров НОПРИЗ/НОСТРОЙ с сервера GitHub: что доступно и в каком виде.

Печатает в журнал запуска коды ответов, ключи и одну-две сырые записи.
"""
import json
import sys
import time

import requests

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (registry research)", "Content-Type": "application/json",
                  "Accept": "application/json"})


def тело(page=1, size=20, search="", filters=None):
    return {"filters": filters or {}, "page": page, "pageCount": str(size), "searchString": search, "sortBy": {}}


def показать(метка, resp, n=2500):
    try:
        data = resp.json()
    except ValueError:
        print(f"### {метка}: HTTP {resp.status_code}, не JSON: {resp.text[:300]!r}")
        return None
    print(f"### {метка}: HTTP {resp.status_code}")
    if isinstance(data, dict):
        print("   ключи:", list(data.keys()))
        d = data.get("data")
        if isinstance(d, dict):
            print("   data.ключи:", list(d.keys()), "count:", d.get("count"), "total:", d.get("total"))
    print("   ", json.dumps(data, ensure_ascii=False)[:n])
    return data


def попытка(метка, method, url, **kw):
    try:
        r = S.request(method, url, timeout=40, **kw)
        return показать(метка, r)
    except requests.RequestException as exc:
        print(f"### {метка}: {type(exc).__name__}: {exc}")
        return None


for base in ("https://reestr.nopriz.ru", "https://reestr.nostroy.ru"):
    print(f"\n================ {base}")
    попытка("главная", "GET", base + "/")
    попытка("все члены, стр.1", "POST", base + "/api/sro/all/member/list", json=тело(1, 1))
    for url, method, body in (
            ("/api/sro/list", "POST", тело(1, 3)),
            ("/api/sro/all/list", "POST", тело(1, 3)),
            ("/api/sro/list", "GET", None),
            ("/api/sro", "GET", None),
            ("/api/sro/all", "POST", тело(1, 3)),
            ("/api/sro/registry/list", "POST", тело(1, 3)),
            ("/api/sro/all/sro/list", "POST", тело(1, 3))):
        попытка(f"список СРО {method} {url}", method, base + url, json=body) if body else \
            попытка(f"список СРО {method} {url}", method, base + url)
        time.sleep(0.5)

base = "https://reestr.nopriz.ru"
print("\n================ карточка и члены одной СРО НОПРИЗ (397 — СФЕРА проектировщиков)")
for url, method in (("/api/sro/397", "GET"), ("/api/sro/397/info", "GET"), ("/api/sro/view/397", "GET")):
    попытка(f"карточка {url}", method, base + url)
попытка("члены 397, стр.1", "POST", base + "/api/sro/397/member/list", json=тело(1, 2))
