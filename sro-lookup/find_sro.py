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
from sro_lookup.report import write_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("input", help="xlsx со списком компаний (название и ИНН)")
    parser.add_argument("--output", help="куда записать результат")
    parser.add_argument("--rps", type=float, default=1.0, help="запросов в секунду к реестру")
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
    write_report(rows, target, date.today())

    found = sum(1 for row in rows if row["sro"])
    no_sro = {row["inn"] for row in rows if not row["sro"] and not row["unchecked"]}
    unchecked = {row["inn"] for row in rows if row["unchecked"]}

    print(f"\nКомпаний в файле:      {len(companies)}")
    print(f"Записей о членстве:    {found}")
    print(f"Не состоят в СРО:      {len(no_sro)}")
    if unchecked:
        print(f"ПРОВЕРКА НЕ ВЫПОЛНЕНА: {len(unchecked)} — реестр не ответил, запустите позже")
    print(f"\nГотово: {target}")


if __name__ == "__main__":
    main()
