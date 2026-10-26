"""Отсев до Checko: не тратить лимит на компании, которые заведомо не подходят.

Подходит строительная компания Москвы, которая действует. Три вопроса —
Москва ли, основной ОКВЭД стройка ли (41, 42, 43), не ликвидирована ли —
бесплатно отвечает своя база mosstroybase.sqlite3. Она собрана из реестра
МСП ФНС, и в неё попали только компании с юридическим адресом в Москве
(код региона 77) и строительным ОКВЭД — основным или дополнительным;
ликвидированных реестр МСП исключает.

Скрипт ставит в файл очереди колонку «Не пробивать» с причиной:

* основной ОКВЭД по базе — не стройка (строительный только дополнительный);
* в базе компания ликвидирована или не в Москве (по прошлым проверкам);
* компании нет в базе — значит, по реестру МСП она не Москва, без
  строительного ОКВЭД или ликвидирована. Так же выпадают крупные компании
  (больше 250 человек): их нет в реестре МСП. Вернуть их в очередь —
  флаг --пробивать-ненайденные.

checko_контакты.py такие строки не спрашивает. Остальных он спрашивает
ради свежего статуса и действующего адреса: база — снимок на дату сборки.

ЗАПУСК (из папки со скриптами, база лежит там же):

    python отсев_до_checko.py --file москва_для_checko.xlsx

Строки, по которым Checko уже ответил, не трогаются. Запускать можно
повторно — отметки пересчитываются по базе заново.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sqlite3
import sys
from collections import Counter
from pathlib import Path

_ЗДЕСЬ = Path(__file__).resolve().parent


def _модуль(имя: str, файл: str):
    spec = importlib.util.spec_from_file_location(имя, _ЗДЕСЬ / файл)
    модуль = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(модуль)
    return модуль


checko = _модуль("checko_контакты", "checko_контакты.py")

СТРОЙКА = ("41", "42", "43")
ОКВЭД_БАЗЫ = "ОКВЭД основной (база МСП)"
НЕТ_В_БАЗЕ = ("нет в базе реестра МСП: не Москва, без строительного ОКВЭД, "
              "ликвидирована или крупная компания")


def из_базы(путь: Path, инны: list[str]) -> tuple[dict[str, dict], str]:
    """{ИНН: строка базы}, дата последнего обновления базы."""
    con = sqlite3.connect(f"file:{путь}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    найдено: dict[str, dict] = {}
    try:
        for i in range(0, len(инны), 500):
            часть = инны[i:i + 500]
            for r in con.execute(
                    "SELECT inn, region_code, okved_main, is_active, egrul_status "
                    f"FROM companies WHERE inn IN ({','.join('?' * len(часть))})", часть):
                найдено[r["inn"]] = dict(r)
        дата = con.execute("SELECT MAX(updated_at) FROM companies").fetchone()[0] or ""
    finally:
        con.close()
    return найдено, str(дата)[:10]


def причина(запись: dict | None, пробивать_ненайденные: bool) -> str:
    """Почему не пробивать; пустая строка — пробивать."""
    if запись is None:
        return "" if пробивать_ненайденные else НЕТ_В_БАЗЕ
    статус = (запись.get("egrul_status") or "").lower()
    if запись.get("is_active") == 0 or any(с in статус for с in ("ликвид", "прекращ", "исключ")):
        return f"ликвидирована или не действует (база: {запись.get('egrul_status') or 'не действует'})"
    регион = (запись.get("region_code") or "").strip()
    if регион and регион != "77":
        return f"не Москва (база: регион {регион})"
    оквэд = (запись.get("okved_main") or "").strip()
    if оквэд and not оквэд.startswith(СТРОЙКА):
        return f"основной ОКВЭД {оквэд} — не стройка (база МСП)"
    return ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Отметить в очереди тех, кого не надо пробивать в Checko")
    p.add_argument("--file", required=True, help="файл очереди для checko_контакты.py")
    p.add_argument("--база", default="mosstroybase.sqlite3", help="база реестра МСП")
    p.add_argument("--пробивать-ненайденные", dest="пробивать_ненайденные", action="store_true",
                   help="компаний, которых нет в базе, не отсеивать (крупные, новые)")
    args = p.parse_args(argv)

    путь, база = Path(args.file), Path(args.база)
    if not путь.exists():
        print(f"Нет файла {путь}", file=sys.stderr)
        return 1
    if not база.exists():
        print(f"Нет базы {база}. Перенесите mosstroybase.sqlite3 в папку со скриптами "
              "(с компьютера, где она собиралась) или укажите путь: --база <путь>", file=sys.stderr)
        return 1

    шапка, строки = checko.read_rows(путь)
    колонка_инн = "ИНН"
    if колонка_инн not in шапка:
        print(f"В файле нет колонки «{колонка_инн}»", file=sys.stderr)
        return 1

    def инн(r: dict) -> str:
        return "".join(ch for ch in r.get(колонка_инн) or "" if ch.isdigit())

    ждут = [r for r in строки if инн(r) and not checko.пробита(r)]
    найдено, дата = из_базы(база, sorted({инн(r) for r in ждут}))

    итог: Counter = Counter()
    for r in ждут:
        запись = найдено.get(инн(r))
        r[ОКВЭД_БАЗЫ] = (запись or {}).get("okved_main") or ""
        r[checko.НЕ_ПРОБИВАТЬ] = причина(запись, args.пробивать_ненайденные)
        if not r[checko.НЕ_ПРОБИВАТЬ]:
            итог["пробивать"] += 1
        elif r[checko.НЕ_ПРОБИВАТЬ] == НЕТ_В_БАЗЕ:
            итог["нет в базе"] += 1
        else:
            итог[r[checko.НЕ_ПРОБИВАТЬ].split(" (")[0].split(" — ")[-1]] += 1

    колонки = list(шапка)
    # вставляются сразу после ИНН, поэтому в обратном порядке: ИНН, «Не пробивать», ОКВЭД
    for новая in (ОКВЭД_БАЗЫ, checko.НЕ_ПРОБИВАТЬ):
        if новая not in колонки:
            колонки.insert(колонки.index(колонка_инн) + 1, новая)
    checko.write_rows(путь, колонки, строки)

    пробивать = итог.pop("пробивать", 0)
    print(f"[отсев] база {база.name}" + (f", обновлена {дата}" if дата else "")
          + f"; ждут пробивки {len(ждут)} компаний")
    print(f"[отсев] пробивать в Checko: {пробивать} — это примерно "
          f"{math.ceil(пробивать / 100) if пробивать else 0} дн. при 100 запросах в сутки")
    for что, сколько in итог.most_common():
        print(f"[отсев] не пробивать — {что}: {сколько}")
    print(f"[отсев] отметки записаны в {путь} (колонка «{checko.НЕ_ПРОБИВАТЬ}»)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
