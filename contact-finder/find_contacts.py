#!/usr/bin/env python3
"""contact-finder — CLI.

Ищет телефоны/почту/сайты компаний по списку «Организация + ИНН» и пишет
результат в xlsx. Работает НА ВАШЕЙ машине, где нет корпоративных блокировок.

Примеры:
    python3 find_contacts.py --in company_list.xlsx --out result.xlsx
    python3 find_contacts.py --in list.xlsx --only-missing prev_result.xlsx
    python3 find_contacts.py --in list.xlsx --sources checko --limit 10 -v

Ключи API кладите в файл .env рядом с программой (см. .env.example).
"""
from __future__ import annotations

import argparse
import sys
import time

from cf.cache import shared as shared_cache
from cf.config import Config
from cf.extract import inn_checksum_valid
from cf.io_xlsx import read_companies, read_found_inns, write_results
from cf.orchestrator import run


def _progress(i: int, total: int, company) -> None:
    phones = company.phones_display or "—"
    mark = "✓" if company.phones else " "
    print(f"[{i:>3}/{total}] {mark} {company.name[:38]:<38} ИНН {company.inn:<13} {phones}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="find_contacts",
        description="Многоисточниковый пробив контактов компаний по ИНН.",
    )
    p.add_argument("--in", dest="inp", required=True, help="входной xlsx/csv (Организация, ИНН)")
    p.add_argument("--out", dest="out", default="contacts_result.xlsx", help="выходной файл")
    p.add_argument("--only-missing", metavar="FILE",
                   help="пропустить ИНН, у которых телефон уже найден в этом файле (экономит квоту API)")
    p.add_argument("--sources", help="только эти источники через запятую: checko,datanewton,aggregators,site,directories")
    p.add_argument("--delay", type=float, default=1.5, help="пауза между запросами к хосту, сек")
    p.add_argument("--timeout", type=float, default=25.0, help="таймаут запроса, сек")
    p.add_argument("--retries", type=int, default=3, help="число попыток на запрос")
    p.add_argument("--workers", type=int, default=1, help="параллельных потоков (осторожно!)")
    p.add_argument("--max-sites", type=int, default=3, help="доменов-кандидатов на сайт компании")
    p.add_argument("--limit", type=int, default=0, help="обработать только первые N (0 = все)")
    p.add_argument("--no-cache", action="store_true", help="игнорировать кэш (осторожно: жжёт квоту API)")
    p.add_argument("--check-inn", action="store_true", help="проверить контрольные цифры ИНН и выйти")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    companies = read_companies(args.inp)
    if not companies:
        print("Не удалось прочитать ни одной строки (нужны столбцы: Организация, ИНН).")
        return 2

    if args.check_inn:
        bad = [c for c in companies if not inn_checksum_valid(c.inn)]
        print(f"Всего: {len(companies)}. ИНН с неверной контрольной суммой: {len(bad)}")
        for c in bad:
            print(f"  ✗ {c.inn}  {c.name}")
        return 0

    # Пропускаем то, что уже найдено раньше, — это главная экономия квоты API.
    skipped = 0
    if args.only_missing:
        done = read_found_inns(args.only_missing)
        before = len(companies)
        companies = [c for c in companies if c.inn not in done]
        skipped = before - len(companies)

    if args.limit:
        companies = companies[: args.limit]
    if not companies:
        print("Нечего обрабатывать: по всем строкам телефон уже найден.")
        return 0

    cfg = Config.from_env()
    cfg.delay = args.delay
    cfg.timeout = args.timeout
    cfg.retries = args.retries
    cfg.max_sites = args.max_sites
    cfg.verbose = args.verbose
    cfg.no_cache = args.no_cache

    # Фильтр источников.
    if args.sources:
        import cf.sources as S
        wanted = {s.strip().lower() for s in args.sources.split(",")}
        alias = {
            "checko": "checko_api", "datanewton": "datanewton_api",
            "aggregators": "aggregator_cards", "site": "company_site",
            "directories": "map_directories",
        }
        names = {alias.get(w, w) for w in wanted}
        S.SOURCES[:] = [s for s in S.SOURCES if s.__name__ in names]
        if not S.SOURCES:
            print(f"Неизвестные источники: {args.sources}")
            return 2

    print(f"Компаний к обработке: {len(companies)}" + (f" (пропущено уже найденных: {skipped})" if skipped else ""))
    print(f"Потоков: {args.workers} | пауза: {cfg.delay}s | кэш: {'выкл' if cfg.no_cache else 'вкл'}")
    keys = [name for name, val in (
        ("Checko", cfg.checko_key), ("Datanewton", cfg.datanewton_key),
        ("2ГИС", cfg.dgis_key), ("Яндекс XML", cfg.yandex_key)) if val]
    print("Ключи API: " + (", ".join(keys) if keys else "нет (работают только бесплатные веб-источники)"))
    print("-" * 78)

    started = time.time()
    run(companies, cfg, workers=args.workers, progress=_progress)

    out_path = write_results(args.out, companies)
    found = sum(1 for c in companies if c.phones)
    cached, cache_path = shared_cache().stats()
    print("-" * 78)
    print(f"Готово за {time.time() - started:.0f}с. Телефон найден: {found}/{len(companies)}")
    print(f"Файл: {out_path}")
    print(f"Кэш: {cached} ответов в {cache_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
