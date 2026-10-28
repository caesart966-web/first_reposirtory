#!/usr/bin/env python3
"""Отправка страниц X-PTO в IndexNow — Яндекс и Bing узнают о них сразу.

Запускает робот GitHub «X-PTO: отправить страницы в IndexNow»
(.github/workflows/indexnow-pto.yml) кнопкой Run workflow ПОСЛЕ заливки
архива на хостинг. Из среды, где собирается сайт, адреса IndexNow закрыты,
а у GitHub доступ есть. Google в IndexNow не участвует — для него Search Console.

    python3 tools/indexnow.py                  # список из pto-site/indexnow.txt
    python3 tools/indexnow.py /slovar/ /stati/ # только эти адреса
    python3 tools/indexnow.py --all            # все страницы из карты сайта

Перед отправкой проверяет на живом сайте:
1. файл ключа <ключ>.txt открывается и содержит ключ — иначе IndexNow ответит 403;
2. каждый адрес есть в карте сайта на хостинге — если нет, значит новый архив
   ещё не залит, и звать робота на несуществующие страницы бессмысленно.
Только стандартная библиотека Python.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
KEY = SITE["seo"].get("indexnow_key", "")
# Адреса в отправке — всегда боевой домен из site.json. Переменные ниже нужны
# только для проверки самого скрипта на локальной копии сайта и заглушке API.
PUBLIC = SITE["base_url"].rstrip("/")
HOST = re.sub(r"^https?://", "", PUBLIC)
BASE = os.environ.get("INDEXNOW_SITE_BASE", PUBLIC).rstrip("/")
API = os.environ.get("INDEXNOW_API", "https://api.indexnow.org/indexnow")
UA = {"User-Agent": "Mozilla/5.0 (compatible; x-pto indexnow)"}


def fail(msg):
    print(f"✗ {msg}")
    sys.exit(1)


def get(path):
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8")


def main():
    args = sys.argv[1:]
    if not re.fullmatch(r"[0-9a-zA-Z-]{8,128}", KEY):
        fail("в data/site.json → seo.indexnow_key нет ключа")
    try:
        key_text = get(f"/{KEY}.txt")
    except Exception as e:
        fail(f"файл ключа /{KEY}.txt не открылся ({e}) — залейте свежий архив сайта")
    if key_text.strip() != KEY:
        fail(f"файл /{KEY}.txt на сайте есть, но в нём не ключ")
    print("✓ Файл ключа на месте.")

    try:
        sitemap = get("/sitemap.xml")
    except Exception as e:
        fail(f"карта сайта не открылась: {e}")
    live = {re.sub(r"^https?://[^/]+", "", u) for u in re.findall(r"<loc>([^<]+)</loc>", sitemap)}

    if "--all" in args:
        paths = sorted(live)
    elif [a for a in args if a.startswith("/")]:
        paths = [a for a in args if a.startswith("/")]
    else:
        lst = ROOT / "indexnow.txt"
        paths = [l.strip() for l in lst.read_text(encoding="utf-8").splitlines()
                 if l.strip().startswith("/")] if lst.exists() else []
    if not paths:
        fail("список адресов пуст")
    missing = [p for p in paths if p not in live]
    if missing:
        fail("этих адресов нет в карте сайта на хостинге — новый архив ещё не залит?\n  "
             + "\n  ".join(missing))

    urls = [PUBLIC + p for p in paths]
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"{PUBLIC}/{KEY}.txt",
                       "urlList": urls}).encode("utf-8")
    req = urllib.request.Request(API, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8", **UA})
    hints = {403: "ключ не подтверждён — файл ключа на сайте не тот",
             422: "адреса не совпадают с доменом", 429: "слишком частая отправка — попробуйте завтра"}
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        fail(f"отказ {e.code}: {hints.get(e.code, e.reason)}")
    print(f"✓ Принято ({code}). Отправлено адресов: {len(urls)}")
    for u in urls:
        print("  " + u)


if __name__ == "__main__":
    main()
