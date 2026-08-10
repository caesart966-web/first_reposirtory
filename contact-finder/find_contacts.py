#!/usr/bin/env python3
"""contact-finder — CLI.

Ищет телефоны/почту/сайты компаний по списку «Организация + ИНН» и пишет
результат в xlsx. Работает НА ВАШЕЙ машине, где нет корпоративных блокировок.

Примеры:
    python3 find_contacts.py --in company_list.xlsx --out result.xlsx
    python3 find_contacts.py --in list.csv --workers 4 --delay 2 -v
    python3 find_contacts.py --in list.xlsx --only-missing result_prev.xlsx

Ключи внешних API (необязательно, повышают полноту) — через переменные среды:
    DGIS_API_KEY, YANDEX_XML_USER, YANDEX_XML_KEY, CF_PROXY
"""
from __future__ import annotations

import argparse
import sys
import time

from cf.config import Config
from cf.extract import inn_checksum_valid
from cf.io_xlsx import read_companies, write_results
from cf.orchestrator import run


def _progress(i: int, total: int, company) -> None:
    phones = company.phones_display or "—"
    mark = "✓" if company.phones else " "
    print(f"[{i:>3}/{total}] {mark} {company.name[:40]:<40} ИНН {company.inn:<12} {phones}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="find_contacts",
        description="Многоисточниковый пробив контактов компаний по ИНН.",
    )
    p.add_argument("--in", dest="inp", required=True, help="входной xlsx/csv (Организация, ИНН)")
    p.add_argument("--out", dest="out", default="contacts_result.xlsx", help="выходной файл")
    p.add_argument("--delay", type=float, default=1.5, help="пауза между запросами к хосту, сек")
    p.add_argument("--timeout", type=float, default=25.0, help="таймаут запроса, сек")
    p.add_argument("--retries", type=int, default=3, help="число попыток на запрос")
    p.add_argument("--workers", type=int, default=1, help="параллельных потоков (осторожно!)")
    p.add_argument("--max-sites", type=int, default=3, help="доменов-кандидатов на сайт компании")
    p.add_argument("--limit", type=int, default=0, help="обработать только первые N (0 = все)")
    p.add_argument("--check-inn", action="store_true", help="проверить контрольные цифры ИНН и выйти")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    companies = read_companies(args.inp)
    if args.limit:
        companies = companies[: args.limit]
    if not companies:
        print("Не удалось прочитать ни одной строки (нужны столбцы: Организация, ИНН).")
        return 2

    if args.check_inn:
        bad = [c for c in companies if not inn_checksum_valid(c.inn)]
        print(f"Всего: {len(companies)}. ИНН с неверной контрольной суммой: {len(bad)}")
        for c in bad:
            print(f"  ✗ {c.inn}  {c.name}")
        return 0

    cfg = Config.from_env()
    cfg.delay = args.delay
    cfg.timeout = args.timeout
    cfg.retries = args.retries
    cfg.max_sites = args.max_sites
    cfg.verbose = args.verbose

    print(f"Компаний к обработке: {len(companies)} | потоков: {args.workers} | пауза: {cfg.delay}s")
    if cfg.dgis_key:
        print("2ГИС API: ключ найден")
    if cfg.yandex_key:
        print("Яндекс XML: ключ найден")
    print("-" * 78)

    started = time.time()
    run(companies, cfg, workers=args.workers, progress=_progress)

    out_path = write_results(args.out, companies)
    found = sum(1 for c in companies if c.phones)
    print("-" * 78)
    print(f"Готово за {time.time() - started:.0f}с. Телефон найден: {found}/{len(companies)}")
    print(f"Файл: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
