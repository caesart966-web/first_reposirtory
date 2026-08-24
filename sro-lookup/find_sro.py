#!/usr/bin/env python3
"""
В каких СРО состоят компании из списка.

Источник — открытые реестры НОСТРОЙ (строители) и НОПРИЗ (проектировщики
и изыскатели). Оба бесплатны, ключей и лимитов нет.

    python3 find_sro.py компании.xlsx

Во входном файле достаточно названия и ИНН — в любом порядке, с шапкой или
без: колонки определяются по содержимому. Результат ложится рядом с исходным
файлом с пометкой «_СРО».
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sro_lookup.config import Settings
from sro_lookup.logging_setup import setup_logging
from sro_lookup.lookup import lookup_companies
from sro_lookup.reader import read_companies
from sro_lookup.report import all_negative_warning, write_report
from sro_lookup.target import NO, UNKNOWN, YES, mark_target


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("input", help="xlsx со списком компаний (название и ИНН)")
    parser.add_argument("--output", help="куда записать результат")
    parser.add_argument("--rps", type=float, default=1.0, help="запросов в секунду к реестру")
    parser.add_argument(
        "--target-sro",
        default="",
        help='отдельная колонка «состоит ли в этой СРО», например: --target-sro "ОРС"',
    )
    args = parser.parse_args()

    source = Path(args.input)
    if not source.exists():
        raise SystemExit(f"Файл не найден: {source}")

    target = Path(args.output) if args.output else source.with_name(f"{source.stem}_СРО.xlsx")
    work_dir = target.parent / "output"
    setup_logging(work_dir / "logs", "INFO")

    companies = read_companies(source)
    if not companies:
        raise SystemExit(
            "В файле не нашлось ни одного корректного ИНН.\n"
            "Нужны колонки с названием и ИНН — порядок и шапка не важны."
        )

    print(f"Компаний к проверке: {len(companies)}\n")
    settings = Settings(nostroy_rps=args.rps, sample_dir=str(work_dir))
    rows = lookup_companies(companies, settings)
    if args.target_sro:
        rows = mark_target(rows, args.target_sro)
    write_report(rows, target, date.today(), target_label=args.target_sro)

    found = sum(1 for row in rows if row["sro"])
    no_sro = {row["inn"] for row in rows if not row["sro"] and not row["unchecked"]}
    unchecked = {row["inn"] for row in rows if row["unchecked"]}

    print(f"\nКомпаний в файле:      {len(companies)}")
    print(f"Записей о членстве:    {found}")
    print(f"Не состоят в СРО:      {len(no_sro)}")
    if unchecked:
        print(f"ПРОВЕРКА НЕ ВЫПОЛНЕНА: {len(unchecked)} — реестр не ответил, запустите позже")

    if args.target_sro:
        by_inn = {row["inn"]: row.get("target") for row in rows}
        print(f"\nСостоят в {args.target_sro}:")
        print(f"  да:           {sum(1 for v in by_inn.values() if v == YES)}")
        print(f"  нет:          {sum(1 for v in by_inn.values() if v == NO)}")
        print(f"  не проверено: {sum(1 for v in by_inn.values() if v == UNKNOWN)}")

    warning = all_negative_warning(rows)
    if warning:
        print("\n" + "=" * 70)
        print(warning)
        print("=" * 70)

    print(f"\nГотово: {target}")


if __name__ == "__main__":
    main()
