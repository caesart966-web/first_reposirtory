"""Сведения об организации по ИНН из Checko — для анализа СРО: карточка,
бухгалтерская отчётность (у НКО — отчёт о целевом использовании средств,
где видны членские взносы), арбитражные дела, проверки, исполнительные
производства. Ответы сохраняются как есть, в один JSON — разбирается он
уже при анализе: так ни одно поле не теряется из-за того, что разбор
о нём не знал.

ЗАПУСК (из папки C:\\mosstroybase):

    set CHECKO_API_KEY=ваш_ключ
    python сро_checko.py --inn 7713387201 --out etm_checko.json

Тратит 5 запросов из суточного лимита, плюс по одному на каждую следующую
страницу арбитражных дел (не больше 10).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

API = "https://api.checko.ru/v2/"
РАЗДЕЛЫ = ("company", "finances", "legal-cases", "inspections", "enforcements")
API_KEY_ENV = "CHECKO_API_KEY"
МАКС_СТРАНИЦ = 10


def _страниц(payload: Any) -> int:
    """Сколько страниц у раздела, если Checko это сообщает (поле зовут
    по-разному — ищем по смыслу)."""
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        for ключ in ("СтрВсего", "Страниц", "pages", "total_pages"):
            v = data.get(ключ)
            if isinstance(v, int) and v > 0:
                return v
    return 1


def спросить(session, раздел: str, inn: str, key: str, страница: int | None = None,
             timeout: int = 60) -> tuple[Any, str]:
    params = {"key": key, "inn": inn}
    if страница:
        params["page"] = страница
    try:
        resp = session.get(API + раздел, params=params, timeout=timeout)
    except requests.RequestException as exc:
        return None, f"сеть: {type(exc).__name__}"
    try:
        payload = resp.json()
    except ValueError:
        payload = None
    if resp.status_code != 200:
        return payload, f"HTTP {resp.status_code}"
    if payload is None:
        return None, "ответ не разобрался"
    meta = payload.get("meta") if isinstance(payload, dict) else None
    if isinstance(meta, dict) and str(meta.get("status", "")).lower() == "error":
        return payload, str(meta.get("message") or "ошибка")
    return payload, ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Сведения об организации из Checko — в один JSON")
    p.add_argument("--inn", required=True, help="ИНН организации (СРО)")
    p.add_argument("--out", default=None, help="куда сохранить (по умолчанию checko_<ИНН>.json)")
    p.add_argument("--key", default=None, help=f"ключ Checko (или переменная {API_KEY_ENV})")
    p.add_argument("--delay", type=float, default=1.0, help="пауза между запросами, сек")
    args = p.parse_args(argv)

    key = args.key or os.environ.get(API_KEY_ENV)
    if not key:
        print(f"Нужен ключ Checko: --key <ключ> или set {API_KEY_ENV}=<ключ>", file=sys.stderr)
        return 1
    inn = "".join(ch for ch in args.inn if ch.isdigit())
    out = Path(args.out or f"checko_{inn}.json")

    session = requests.Session()
    итог: dict[str, Any] = {"инн": inn, "собрано": datetime.now().isoformat(timespec="seconds"),
                            "ответы": {}, "ошибки": {}}
    стоп = ""
    for раздел in РАЗДЕЛЫ:
        payload, ошибка = спросить(session, раздел, inn, key)
        if ошибка:
            итог["ошибки"][раздел] = ошибка
            print(f"[checko] {раздел}: {ошибка}", flush=True)
            if ошибка.startswith(("HTTP 401", "HTTP 402", "HTTP 403", "HTTP 429")):
                стоп = ошибка
                break
            continue
        страницы = [payload]
        всего = min(_страниц(payload), МАКС_СТРАНИЦ)
        for n in range(2, всего + 1):
            time.sleep(args.delay)
            ещё, ошибка = спросить(session, раздел, inn, key, страница=n)
            if ошибка:
                итог["ошибки"][f"{раздел} стр. {n}"] = ошибка
                break
            страницы.append(ещё)
        итог["ответы"][раздел] = страницы if len(страницы) > 1 else payload
        print(f"[checko] {раздел}: получено" + (f", страниц {len(страницы)}" if len(страницы) > 1 else ""),
              flush=True)
        time.sleep(args.delay)

    out.write_text(json.dumps(итог, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[checko] сохранено: {out}")
    if стоп:
        print(f"[checko] остановка: {стоп} — похоже, кончился лимит; запустите завтра")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
