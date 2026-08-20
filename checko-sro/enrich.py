#!/usr/bin/env python3
"""Добирает недостающие поля через API Чеко и складывает их в кэш.

Ключ берётся из переменной окружения CHECKO_API_KEY — в репозиторий он
не попадает. Скрипт сам следит за суточным лимитом в 100 запросов и
останавливается, не тратя лишнего; уже пробитые ИНН не запрашиваются повторно.

    export CHECKO_API_KEY='ваш-ключ'
    python3 enrich.py --source final_report_20260820.xlsx --limit 3   # проба
    python3 enrich.py --source final_report_20260820.xlsx             # весь день
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_report import SRC_ADDR, SRC_EMAIL, SRC_HEAD, SRC_INN, SRC_NAME, SRC_PHONE, read_source
from lib.address import detect_shared_addresses, pick_address
from lib.checko import CheckoClient, QuotaExhausted, extract
from lib.names import director_from_ip_name


def plan(source_rows, client, all_addresses=False):
    """ИНН, которым нужен запрос, в порядке важности пропуска.

    Адрес и руководитель важнее контактов: без них строка отчёта неполна,
    а телефона у компании может не быть в принципе.

    all_addresses=True добавляет в очередь и те строки, где адрес выбран
    эвристикой: запрос к Чеко заменит выбор на юридический адрес из ЕГРЮЛ.
    """
    shared = detect_shared_addresses(source_rows, address_index=SRC_ADDR)
    tasks = []
    for row in source_rows:
        inn = str(row[SRC_INN]).strip()
        if client.cached(inn) is not None:
            continue

        address, ambiguous = pick_address(row[SRC_ADDR], inn, shared)
        director = row[SRC_HEAD] or director_from_ip_name(row[SRC_NAME])

        weight, missing = 0, []
        if not address:
            weight += 100
            missing.append("адрес")
        elif ambiguous:
            weight += 50
            missing.append("адрес неоднозначен")
        if not director:
            weight += 40
            missing.append("руководитель")
        if not row[SRC_PHONE]:
            weight += 10
            missing.append("телефон")
        if not row[SRC_EMAIL]:
            weight += 5
            missing.append("email")

        if not weight and all_addresses and address:
            weight, missing = 1, ["сверить адрес с ЕГРЮЛ"]

        if weight:
            tasks.append((weight, inn, row[SRC_NAME], ", ".join(missing)))

    tasks.sort(key=lambda t: -t[0])
    return tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="xlsx первого прогона")
    parser.add_argument("--cache", default="cache/checko", help="куда складывать ответы")
    parser.add_argument("--limit", type=int, help="ограничить число запросов за прогон")
    parser.add_argument("--dry-run", action="store_true", help="только показать план")
    parser.add_argument(
        "--all-addresses",
        action="store_true",
        help="запросить юридический адрес по всем ИНН, а не только там, где его нет",
    )
    args = parser.parse_args()

    api_key = os.environ.get("CHECKO_API_KEY")
    if not api_key and not args.dry_run:
        parser.error("не задана переменная окружения CHECKO_API_KEY")

    client = CheckoClient(api_key or "", args.cache)
    tasks = plan(read_source(args.source), client, all_addresses=args.all_addresses)
    budget = client.quota_left()
    if args.limit is not None:
        budget = min(budget, args.limit)

    print(f"Нужен запрос: {len(tasks)} ИНН")
    print(f"Остаток суточного лимита: {client.quota_left()} из {client.daily_limit}")
    print(f"Будет запрошено сейчас: {min(len(tasks), budget)}\n")

    if args.dry_run:
        for weight, inn, name, missing in tasks[:30]:
            print(f"  {inn:<13} {str(name)[:44]:<44} — {missing}")
        if len(tasks) > 30:
            print(f"  … и ещё {len(tasks) - 30}")
        return

    done = failed = 0
    for weight, inn, name, missing in tasks[:budget]:
        try:
            fields = extract(client.fetch(inn))
        except QuotaExhausted as error:
            print(f"\nОстановка: {error}")
            break
        except Exception as error:  # сеть, таймаут, битый ответ
            failed += 1
            print(f"  ! {inn} {str(name)[:40]} — {type(error).__name__}: {error}")
            continue
        done += 1
        got = [k for k in ("address", "director") if fields.get(k)]
        got += ["phones"] if fields.get("phones") else []
        got += ["emails"] if fields.get("emails") else []
        print(f"  + {inn} {str(name)[:40]:<40} получено: {', '.join(got) or 'пусто'}")

    print(f"\nЗапросов сделано: {client.requests_made}  ошибок: {failed}")
    print(f"Остаток лимита на сегодня: {client.quota_left()}")
    print(f"Осталось непробитых ИНН: {max(0, len(tasks) - done)}")
    print("\nДальше: python3 build_report.py --source", args.source)


if __name__ == "__main__":
    main()
