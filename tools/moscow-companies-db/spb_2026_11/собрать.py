"""Сводка по строительным СРО Санкт-Петербурга из реестра НОСТРОЙ.

Что делает:
  1. POST /api/sro/list — список всех СРО, по нему регистрационный номер
     переводится в id реестра (id ≠ рег. номер).
  2. POST /api/sro/{id} — карточка СРО (названия, ИНН, ОГРН, адрес, телефон).
  3. POST /api/sro/{id}/member/list — все записи членов СРО постранично
     (pageCount — строкой), с проверкой «заявлено = получено».
  4. POST /api/member/{id}/info — карточка члена, только для исключённых:
     дата исключения есть ТОЛЬКО здесь — поле data.suspension_date
     (основание — data.suspension_reason). Запасные источники по порядку:
     data.right.actions[] с suspension_decision.code == "4" («Прекращение
     действия права») → basis_date; затем data.last_updated_at
     (помечается как приблизительная дата).
  5. Пишет сводка.json: только сводные числа и сведения о самих СРО.

Сырые ответы (списки членов, карточки) кладутся в кэш ВНЕ репозитория
(--кэш, по умолчанию ~/.cache/nostroy_spb) — в них данные физлиц, их не
коммитить. Повторный запуск докачивает недостающие карточки из кэша.

  python собрать.py                    # всё: списки + карточки + сводка
  python собрать.py --заново-списки    # перекачать списки членов
  python собрать.py --только-сводка    # пересчитать по кэшу без сети
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

import requests

BASE = "https://reestr.nostroy.ru/api"
PAGE = 500
ПАУЗА = (0.3, 0.5)

СРО_СПБ = [
    "СРО-С-003-22042009", "СРО-С-008-19052009", "СРО-С-048-12102009",
    "СРО-С-063-09112009", "СРО-С-064-09112009", "СРО-С-144-23122009",
    "СРО-С-151-24122009", "СРО-С-157-25122009", "СРО-С-169-11012010",
    "СРО-С-180-20012010", "СРО-С-200-16022010", "СРО-С-221-30042010",
    "СРО-С-231-14122010", "СРО-С-287-15092017", "СРО-С-303-22122020",
    "СРО-С-322-27022025", "СРО-С-328-25062025", "СРО-С-335-25122025",
    "СРО-С-338-20032026",
]
ГОДЫ = (2023, 2024, 2025, 2026)
СТАТУС_ДЕЙСТВ = "Является членом"
СТАТУС_ИСКЛ = "Исключен"

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (registry statistics)",
                  "Accept": "application/json, text/plain, */*",
                  "Content-Type": "application/json"})


def post(path: str, body: dict | None = None, попыток: int = 7) -> dict:
    """POST с паузой между запросами и повтором при 429/5xx и сетевых сбоях."""
    url = f"{BASE}/{path}"
    ждать = 2.0
    for n in range(попыток):
        time.sleep(random.uniform(*ПАУЗА))
        try:
            r = S.post(url, data=json.dumps(body or {}), timeout=90)
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            d = r.json()
            if not d.get("success", True):
                raise requests.HTTPError(f"success=false: {d.get('message')}")
            return d
        except (requests.RequestException, ValueError) as exc:
            if n == попыток - 1:
                raise
            print(f"  повтор {path}: {exc}; жду {ждать:.0f} с", file=sys.stderr)
            time.sleep(ждать)
            ждать *= 2
    raise RuntimeError("недостижимо")


def тело(page: int) -> dict:
    return {"filters": {}, "page": page, "pageCount": str(PAGE),
            "searchString": "", "sortBy": {}}


def список_сро() -> dict[str, dict]:
    d = post("sro/list", тело(1))["data"]
    return {x["registration_number"].strip(): x for x in d["data"]}


def члены_сро(sro_id: int) -> tuple[int, list[dict]]:
    первая = post(f"sro/{sro_id}/member/list", тело(1))["data"]
    заявлено = int(первая["count"])
    страниц = int(первая["countPages"])
    записи = list(первая["data"])
    for p in range(2, страниц + 1):
        записи += post(f"sro/{sro_id}/member/list", тело(p))["data"]["data"]
    # повторы на стыке страниц — убрать по id записи
    по_id = {z["id"]: z for z in записи}
    return заявлено, list(по_id.values())


def дата(s: str | None) -> dt.date | None:
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def дата_исключения(карточка: dict) -> tuple[dt.date | None, str]:
    """(дата, источник): suspension_date → right.actions(код 4) → last_updated_at."""
    if (d := дата(карточка.get("suspension_date"))):
        return d, "suspension_date"
    действия = ((карточка.get("right") or {}).get("actions")) or []
    прекр = [дата(a.get("basis_date")) for a in действия
             if str((a.get("suspension_decision") or {}).get("code")) == "4"]
    прекр = [x for x in прекр if x]
    if прекр:
        return max(прекр), "right.actions"
    if (d := дата(карточка.get("last_updated_at"))):
        return d, "last_updated_at (приблизительно)"
    return None, "нет"


def месяцы(до: dt.date) -> list[str]:
    out, y, m = [], 2023, 1
    while (y, m) <= (до.year, до.month):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--кэш", default=os.path.expanduser("~/.cache/nostroy_spb"))
    ap.add_argument("--out", default=str(Path(__file__).with_name("сводка.json")))
    ap.add_argument("--заново-списки", action="store_true")
    ap.add_argument("--только-сводка", action="store_true")
    a = ap.parse_args()

    кэш = Path(a.кэш)
    (кэш / "списки").mkdir(parents=True, exist_ok=True)
    карточки_файл = кэш / "карточки.jsonl"
    сро_файл = кэш / "сро.json"

    # 1–3. СРО, их карточки и списки членов
    if a.только_сводка:
        сро = json.loads(сро_файл.read_text(encoding="utf-8"))
    else:
        реестр = список_сро()
        сро = {}
        for номер in СРО_СПБ:
            x = реестр.get(номер)
            if not x:
                print(f"{номер}: нет в списке СРО реестра", file=sys.stderr)
                сро[номер] = {"id": None}
                continue
            карт = post(f"sro/{x['id']}")
            сро[номер] = {"id": x["id"], "список": x, "карточка": карт.get("data"),
                          "карточка_обновлена": карт.get("lastUpdateDate")}
            путь = кэш / "списки" / f"{x['id']}.json"
            if a.заново_списки or not путь.exists():
                заявлено, записи = члены_сро(x["id"])
                путь.write_text(json.dumps({"заявлено": заявлено, "записи": записи,
                                            "собрано": dt.datetime.now().isoformat(timespec="seconds")},
                                           ensure_ascii=False), encoding="utf-8")
            сп = json.loads(путь.read_text(encoding="utf-8"))
            print(f"{номер} id={x['id']}: заявлено {сп['заявлено']}, получено {len(сп['записи'])}")
        сро_файл.write_text(json.dumps(сро, ensure_ascii=False), encoding="utf-8")

    # 4. Карточки исключённых (с докачкой)
    карточки: dict[int, dict] = {}
    if карточки_файл.exists():
        for line in карточки_файл.open(encoding="utf-8"):
            if line.strip():
                z = json.loads(line)
                карточки[z["id"]] = z
    нужно = []
    for номер, s in сро.items():
        if not s.get("id"):
            continue
        сп = json.loads((кэш / "списки" / f"{s['id']}.json").read_text(encoding="utf-8"))
        for z in сп["записи"]:
            if (z.get("member_status") or {}).get("title") != СТАТУС_ДЕЙСТВ and z["id"] not in карточки:
                нужно.append(z["id"])
    if нужно and not a.только_сводка:
        print(f"карточек исключённых докачать: {len(нужно)}")
        with карточки_файл.open("a", encoding="utf-8") as f:
            for i, mid in enumerate(нужно, 1):
                d = post(f"member/{mid}/info")["data"]
                карточки[mid] = d
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
                if i % 250 == 0:
                    f.flush()
                    print(f"  {i}/{len(нужно)}", flush=True)

    # 5. Счёт
    сегодня = dt.date.today()
    мес = месяцы(сегодня)
    итог = []
    for номер, s in сро.items():
        if not s.get("id"):
            итог.append({"рег_номер": номер, "id": None, "ошибка": "нет в реестре"})
            continue
        сп = json.loads((кэш / "списки" / f"{s['id']}.json").read_text(encoding="utf-8"))
        записи = сп["записи"]
        статусы = Counter((z.get("member_status") or {}).get("title") for z in записи)
        вступ = Counter()
        искл = Counter()
        вступ_мес = Counter()
        искл_мес = Counter()
        источники = Counter()
        без_даты = 0
        без_карточки = 0
        for z in записи:
            dv = дата(z.get("registry_registration_date"))
            if dv:
                вступ[dv.year] += 1
                вступ_мес[f"{dv.year}-{dv.month:02d}"] += 1
            if (z.get("member_status") or {}).get("title") == СТАТУС_ДЕЙСТВ:
                continue
            к = карточки.get(z["id"])
            if к is None:
                без_карточки += 1
                без_даты += 1
                continue
            di, ист = дата_исключения(к)
            источники[ист] += 1
            if ист != "suspension_date":
                # счёт годов/месяцев — только по точной дате
                без_даты += 1
                continue
            искл[di.year] += 1
            искл_мес[f"{di.year}-{di.month:02d}"] += 1
        к = s.get("карточка") or {}
        итог.append({
            "рег_номер": номер,
            "id": s["id"],
            "страница": f"https://reestr.nostroy.ru/sro/{s['id']}",
            "карточка": {
                "полное_название": к.get("full_description"),
                "краткое_название": к.get("short_description"),
                "инн": к.get("inn"),
                "огрн": к.get("ogrn"),
                "руководитель": None,  # в реестре НОСТРОЙ нет (ни в API, ни в выгрузке)
                "руководитель_должность": None,
                "адрес": к.get("place"),
                "телефон": к.get("phone"),
                "сайт": к.get("site"),
                "email": к.get("email"),
                "город": (s.get("список") or {}).get("region_name"),
                "состояние": (s.get("список") or {}).get("state"),
                "карточка_обновлена_в_реестре": s.get("карточка_обновлена"),
            },
            "заявлено_реестром": сп["заявлено"],
            "получено": len(записи),
            "полнота": "полно" if len(записи) == сп["заявлено"] else "НЕПОЛНО",
            "дата_сбора": сп["собрано"][:10],
            "всего_записей": len(записи),
            "действующих": статусы.get(СТАТУС_ДЕЙСТВ, 0),
            "исключённых_всего": len(записи) - статусы.get(СТАТУС_ДЕЙСТВ, 0),
            "статусы": dict(статусы),
            **{f"вступило_{y}": вступ.get(y, 0) for y in ГОДЫ},
            **{f"исключено_{y}": искл.get(y, 0) for y in ГОДЫ},
            "без_даты_искл": без_даты,
            "исключённых_без_карточки": без_карточки,
            "источник_даты_искл": dict(источники),
            "вступления_по_месяцам": {m: вступ_мес.get(m, 0) for m in мес},
            "исключения_по_месяцам": {m: искл_мес.get(m, 0) for m in мес},
        })
    out = {
        "источник": "reestr.nostroy.ru (API сайта)",
        "дата_сбора": сегодня.isoformat(),
        "пояснения": {
            "дата_вступления": "registry_registration_date из списка членов СРО",
            "дата_исключения": "suspension_date из карточки члена POST /api/member/{id}/info; "
                               "в списках членов этого поля нет",
            "без_даты_искл": "исключённые, у которых в карточке нет suspension_date "
                             "(в годы/месяцы не попадают; см. источник_даты_искл)",
            "записи": "запись = членство; компания, вступившая повторно, даёт две записи",
        },
        "сро": итог,
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"записано: {a.out}")
    for r in итог:
        print(r["рег_номер"], r.get("заявлено_реестром"), r.get("получено"),
              r.get("действующих"), r.get("исключённых_всего"), r.get("без_даты_искл"))


if __name__ == "__main__":
    main()
