"""CLI: сбор базы московских строительных/проектных/изыскательских компаний.

Типовой конвейер:
    fetch-rsmp → build → enrich-egrul → [enrich-checko] → [enrich-sites] → export
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

from . import config, riskscore
from .db import CompanyDB
from .export import export_csv, export_xlsx
from .http import make_session
from .sources import checko, egrul, nopriz, rsmp, sro, website


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        print("\nПрервано пользователем; уже собранные данные сохранены в БД.")
        return 130


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mosstroybase",
        description="Сбор базы строительных, проектных и изыскательских компаний Москвы",
    )
    parser.add_argument(
        "--db", default=config.DEFAULT_DB_PATH,
        help=f"путь к файлу SQLite (по умолчанию {config.DEFAULT_DB_PATH})",
    )
    # --db разрешён и до, и после подкоманды; SUPPRESS не даёт подкоманде
    # затереть значение глобального флага своим default-ом
    db_parent = argparse.ArgumentParser(add_help=False)
    db_parent.add_argument("--db", default=argparse.SUPPRESS, help="путь к файлу SQLite")
    sub = parser.add_subparsers(dest="command", parser_class=argparse.ArgumentParser)

    def add_parser(name: str, **kwargs):
        return sub.add_parser(name, parents=[db_parent], **kwargs)

    p = add_parser("fetch-rsmp", help="скачать выгрузку реестра МСП ФНС (~1.5–2 ГБ)")
    p.add_argument("--out", default="data/rsmp.zip", help="куда сохранить архив")
    p.add_argument("--force", action="store_true", help="перекачать, даже если файл уже есть")
    p.set_defaults(func=cmd_fetch_rsmp)

    p = add_parser("build", help="отобрать компании из выгрузки реестра МСП в базу")
    p.add_argument("--rsmp-file", default="data/rsmp.zip", help="путь к ZIP/XML выгрузки")
    p.add_argument("--region", default=config.MOSCOW_REGION_CODE, help="код региона (77 — Москва)")
    p.add_argument(
        "--okved", nargs="+", default=list(config.DEFAULT_OKVED_PREFIXES),
        help="префиксы ОКВЭД (по умолчанию: %(default)s)",
    )
    p.add_argument("--include-ip", action="store_true", help="включать ИП (по умолчанию только ЮЛ)")
    p.add_argument("--limit", type=int, default=0, help="остановиться после N компаний (для проверки)")
    p.set_defaults(func=cmd_build)

    p = add_parser("import-inn", help="добавить компании списком ИНН (файл, по одному в строке)")
    p.add_argument("--file", required=True, help="текстовый файл с ИНН")
    p.set_defaults(func=cmd_import_inn)

    p = add_parser("enrich-egrul", help="дообогатить из ЕГРЮЛ: e-mail, статус, адрес")
    p.add_argument("--limit", type=int, default=0, help="обработать не более N компаний")
    p.add_argument("--delay", type=float, default=config.DEFAULT_DELAY_EGRUL, help="пауза, сек")
    p.set_defaults(func=cmd_enrich_egrul)

    p = add_parser("enrich-checko", help="телефоны/сайты через Checko API (нужен ключ)")
    p.add_argument("--key", default=None, help=f"API-ключ (или переменная {config.CHECKO_API_KEY_ENV})")
    p.add_argument("--limit", type=int, default=100, help="обработать не более N компаний")
    p.add_argument("--delay", type=float, default=config.DEFAULT_DELAY_CHECKO, help="пауза, сек")
    p.add_argument(
        "--include-inactive", action="store_true",
        help="тратить запросы и на ликвидированные компании (по умолчанию — нет)",
    )
    p.add_argument(
        "--include-with-phones", action="store_true",
        help="запрашивать и компании, у которых телефон уже найден (по умолчанию — нет)",
    )
    p.add_argument(
        "--redo-empty", action="store_true",
        help="повторно запросить компании, обработанные ранее, но оставшиеся "
             "без контактов (тратит квоту заново)",
    )
    p.add_argument(
        "--redo-no-director", action="store_true",
        help="повторно запросить компании с контактами, но без ФИО руководителя — "
             "для пачек, обработанных до появления этого поля (тратит квоту)",
    )
    p.add_argument(
        "--redo-no-liveness", action="store_true",
        help="повторно запросить обработанные компании без признаков живости "
             "(СЧР/налоги/банкротство) — для пачек до появления этих полей "
             "(тратит квоту)",
    )
    p.add_argument(
        "--include-secondary", action="store_true",
        help="брать и компании, у которых строительный ОКВЭД только дополнительный "
             "(по умолчанию — только основной)",
    )
    p.add_argument(
        "--okved", nargs="+", default=list(config.DEFAULT_OKVED_PREFIXES),
        help="какие основные ОКВЭД брать в работу (по умолчанию: %(default)s; "
             "например, --okved 41 42 43 — только стройка, без проектировщиков)",
    )
    p.set_defaults(func=cmd_enrich_checko)

    p = add_parser("enrich-sites", help="собрать контакты с сайтов компаний (где сайт известен)")
    p.add_argument("--limit", type=int, default=0, help="обработать не более N компаний")
    p.add_argument("--delay", type=float, default=config.DEFAULT_DELAY_WEBSITE, help="пауза, сек")
    p.set_defaults(func=cmd_enrich_sites)

    p = add_parser("enrich-sro", help="пометить членов строительных СРО по реестру НОСТРОЙ (бесплатно)")
    p.add_argument("--limit", type=int, default=0, help="проверить не более N компаний")
    p.add_argument("--delay", type=float, default=config.DEFAULT_DELAY_SRO, help="пауза, сек")
    p.add_argument(
        "--recheck", action="store_true",
        help="перепроверить компании, уже помеченные как «не в СРО» "
             "(нужно после исправления фильтра реестра)",
    )
    p.add_argument(
        "--file", default=None,
        help="проверить только ИНН из файла (по одному в строке), а не всю "
             "базу — отсутствующих в базе добавит сам, как import-inn",
    )
    p.add_argument(
        "--out", default=None,
        help="вместе с --file: сохранить результат по этому списку в CSV/XLSX "
             "(по расширению файла) — ИНН, название, членство в СРО",
    )
    p.set_defaults(func=cmd_enrich_sro)

    p = add_parser(
        "enrich-nopriz",
        help="пометить членов проектно-изыскательских СРО по реестру НОПРИЗ "
             "(бесплатно; справочно — на выгрузки не влияет)",
    )
    p.add_argument("--limit", type=int, default=0, help="проверить не более N компаний")
    p.add_argument("--delay", type=float, default=config.DEFAULT_DELAY_SRO, help="пауза, сек")
    p.add_argument(
        "--recheck", action="store_true",
        help="перепроверить компании, уже помеченные как «не в НОПРИЗ»",
    )
    p.add_argument(
        "--file", default=None,
        help="проверить только ИНН из файла (по одному в строке), а не всю "
             "базу — отсутствующих в базе добавит сам, как import-inn",
    )
    p.add_argument(
        "--out", default=None,
        help="вместе с --file: сохранить результат по этому списку в CSV/XLSX "
             "(по расширению файла) — ИНН, название, членство в НОПРИЗ",
    )
    p.set_defaults(func=cmd_enrich_nopriz)

    p = add_parser("daily", help="ежедневный прогон: СРО-фильтр + Checko-пачка + сайты + Excel за сегодня")
    p.add_argument("--key", default=None, help=f"API-ключ Checko (или переменная {config.CHECKO_API_KEY_ENV})")
    p.add_argument("--limit", type=int, default=100, help="размер дневной пачки (по умолчанию 100)")
    p.add_argument("--delay", type=float, default=config.DEFAULT_DELAY_CHECKO, help="пауза, сек")
    p.add_argument("--out-dir", default="exports", help="папка для Excel-файлов (по умолчанию exports/)")
    p.add_argument(
        "--include-secondary", action="store_true",
        help="брать и компании, у которых строительный ОКВЭД только дополнительный "
             "(по умолчанию — только основной)",
    )
    p.add_argument(
        "--okved", nargs="+", default=list(config.DEFAULT_OKVED_PREFIXES),
        help="какие основные ОКВЭД брать в работу (по умолчанию: %(default)s; "
             "например, --okved 41 42 43 — только стройка, без проектировщиков)",
    )
    p.add_argument(
        "--include-risky", action="store_true",
        help="не отсеивать компании с признаками мусора/технички (по умолчанию "
             "отсеиваются — см. --exclude-risky в export)",
    )
    p.set_defaults(func=cmd_daily)

    p = add_parser("export", help="выгрузить базу в CSV/XLSX")
    p.add_argument("--csv", default=None, help="путь к CSV")
    p.add_argument("--xlsx", default=None, help="путь к XLSX (нужен openpyxl)")
    p.add_argument("--only-active", action="store_true", help="только действующие компании")
    p.add_argument(
        "--with-contacts-only", action="store_true",
        help="только компании, у которых найден телефон или e-mail",
    )
    p.add_argument(
        "--include-sro", action="store_true",
        help="включить в выгрузку и членов строительных СРО (по умолчанию отсекаются)",
    )
    p.add_argument(
        "--alive-only", action="store_true",
        help="только компании с признаками жизни: сотрудники (СЧР) > 0 или "
             "уплаченные налоги > 0 (банкроты отсекаются всегда)",
    )
    p.add_argument(
        "--exclude-risky", action="store_true",
        help="отсеять компании с признаками мусора/технички: недостоверность "
             "или предстоящее исключение в ЕГРЮЛ, отсутствие контактов, "
             "0 сотрудников и 0 налогов, парная регистрация по одному адресу "
             "(см. mosstroybase/riskscore.py)",
    )
    p.set_defaults(func=cmd_export)

    p = add_parser("clean-phones", help="вычистить мусорные телефоны из базы")
    p.add_argument(
        "--reharvest-over", type=int, default=6,
        help="компаниям с числом номеров больше N пересобрать телефоны с их "
             "сайта по строгим правилам (0 — отключить; по умолчанию 6)",
    )
    p.add_argument("--delay", type=float, default=config.DEFAULT_DELAY_WEBSITE, help="пауза, сек")
    p.set_defaults(func=cmd_clean_phones)

    p = add_parser("check-sro", help="диагностика: проверить один ИНН по реестру НОСТРОЙ")
    p.add_argument("inn", help="ИНН для проверки")
    p.set_defaults(func=cmd_check_sro)

    p = add_parser("check-nopriz", help="диагностика: проверить один ИНН по реестру НОПРИЗ")
    p.add_argument("inn", help="ИНН для проверки")
    p.set_defaults(func=cmd_check_nopriz)

    p = add_parser("check-checko", help="диагностика: сырой ответ Checko API по одному ИНН")
    p.add_argument("inn", help="ИНН для проверки")
    p.add_argument("--key", default=None, help=f"API-ключ (или переменная {config.CHECKO_API_KEY_ENV})")
    p.set_defaults(func=cmd_check_checko)

    p = add_parser("check-risk", help="диагностика: разбор оценки риска (--exclude-risky) по одному ИНН")
    p.add_argument("inn", help="ИНН для проверки")
    p.set_defaults(func=cmd_check_risk)

    p = add_parser("stats", help="сводка по базе")
    p.set_defaults(func=cmd_stats)

    return parser


# -- команды ------------------------------------------------------------


def cmd_fetch_rsmp(args) -> int:
    session = make_session()
    url = rsmp.resolve_data_url(session)
    rsmp.download(url, Path(args.out), session, force=args.force)
    return 0


def cmd_build(args) -> int:
    path = Path(args.rsmp_file)
    if not path.exists():
        print(f"Файл {path} не найден. Сначала выполните fetch-rsmp "
              "или укажите путь через --rsmp-file.", file=sys.stderr)
        return 1
    prefixes = tuple(args.okved)
    print(f"[build] регион {args.region}, ОКВЭД {', '.join(prefixes)}")
    count = 0
    with CompanyDB(args.db) as db:
        for doc in rsmp.iter_companies(path, args.region, prefixes, include_ip=args.include_ip):
            doc["sources"] = ["rsmp"]
            db.upsert(doc)
            count += 1
            if count % 500 == 0:
                print(f"[build] в базе {count} компаний...")
            if args.limit and count >= args.limit:
                print(f"[build] достигнут лимит {args.limit}, останавливаюсь")
                break
    print(f"[build] готово, добавлено/обновлено компаний: {count}")
    return 0


def cmd_import_inn(args) -> int:
    path = Path(args.file)
    if not path.exists():
        print(f"Файл {path} не найден.", file=sys.stderr)
        return 1
    count = 0
    with CompanyDB(args.db) as db:
        for line in path.read_text(encoding="utf-8").splitlines():
            inn = line.strip()
            if not inn or not inn.isdigit():
                continue
            db.upsert({"inn": inn, "kind": "ЮЛ", "sources": ["manual"]})
            count += 1
    print(f"[import-inn] добавлено ИНН: {count}. Далее выполните enrich-egrul.")
    return 0


def cmd_enrich_egrul(args) -> int:
    session = make_session()
    processed = errors = 0
    with CompanyDB(args.db) as db:
        companies = list(db.iter_missing_source("egrul", limit=0))
        # Сначала — компании, уже прошедшие Checko: это рабочие пачки, им
        # ЕГРЮЛ допишет руководителя, e-mail и полный адрес в первую очередь
        companies.sort(key=lambda c: 0 if "checko" in c["sources"] else 1)
        if args.limit:
            companies = companies[: args.limit]
        total = len(companies)
        print(f"[egrul] к обработке: {total} (первыми идут компании из дневных пачек Checko)")
        for company in companies:
            inn = company["inn"]
            try:
                payload = egrul.fetch(inn, session)
            except requests.RequestException as exc:
                errors += 1
                print(f"[egrul] {inn}: ошибка сети ({exc}), пропускаю")
                if errors >= 20 and errors > processed:
                    print("[egrul] слишком много ошибок подряд — источник недоступен; "
                          "останавливаюсь.\n"
                          "Примечание: бесплатный JSON-доступ зеркала ЕГРЮЛ "
                          "(egrul.itsoft.ru → egrul.org) закрыт и переведён в платную "
                          "подписку. Руководителя, адрес, статус и e-mail рабочим "
                          "пачкам теперь даёт Checko (команда daily) — этот шаг "
                          "перестал быть обязательным.", file=sys.stderr)
                    return 1
                continue
            update: dict = {"inn": inn, "sources": ["egrul"]}
            if payload is None:
                update["egrul_status"] = "не найдено в ЕГРЮЛ"
            else:
                update.update(egrul.extract_info(payload))
            db.upsert(update)
            processed += 1
            if processed % 100 == 0:
                percent = processed * 100 // total if total else 100
                print(f"[egrul] обработано {processed}/{total} ({percent}%)", flush=True)
            time.sleep(args.delay)
    print(f"[egrul] готово: обработано {processed}, ошибок {errors}")
    return 0


def select_for_checko(
    companies: list[dict],
    limit: int,
    include_inactive: bool = False,
    include_with_phones: bool = False,
    okved_prefixes: tuple[str, ...] = config.DEFAULT_OKVED_PREFIXES,
    include_secondary: bool = False,
) -> list[dict]:
    """Отбирает компании под квоту Checko: без лишней траты запросов.

    В работу идут только компании со строительным/проектным ОСНОВНЫМ ОКВЭД
    (include_secondary=True возвращает и те, у кого стройка лишь в доп.
    кодах). Ликвидированные и уже имеющие телефон пропускаются; члены
    строительных СРО не берутся никогда.
    """
    candidates = []
    for company in companies:
        if company.get("sro_member") == 1:
            continue
        if company.get("bankruptcy") == 1:
            continue
        main_ok = rsmp.okved_matches(company.get("okved_main") or "", okved_prefixes)
        if not main_ok and not include_secondary:
            continue
        if not include_inactive and company.get("is_active") == 0:
            continue
        if not include_with_phones and company.get("phones"):
            continue
        candidates.append(company)
    # Порядок: основной ОКВЭД раньше дополнительного; внутри — средние и малые
    # раньше микро (телефоны находятся чаще); внутри категории — свежие по дате
    # включения в реестр МСП первыми (контакты моложе — дозвон выше)
    msp_priority = {"среднее": 0, "малое": 1, "микро": 2}
    candidates.sort(key=lambda c: c.get("msp_since") or "", reverse=True)
    candidates.sort(
        key=lambda c: (
            0 if rsmp.okved_matches(c.get("okved_main") or "", okved_prefixes) else 1,
            msp_priority.get(c.get("msp_category"), 3),
        )
    )
    return candidates[:limit] if limit else candidates


def run_checko_batch(
    db: CompanyDB,
    session,
    api_key: str,
    limit: int,
    delay: float,
    include_inactive: bool = False,
    include_with_phones: bool = False,
    sro_precheck: bool = True,
    pool: list[dict] | None = None,
    include_secondary: bool = False,
    okved_prefixes: tuple[str, ...] = config.DEFAULT_OKVED_PREFIXES,
) -> list[str]:
    """Обрабатывает пачку компаний через Checko; возвращает ИНН обработанных.

    Перед тратой Checko-запроса компания бесплатно проверяется по реестру
    НОСТРОЙ: действующие члены строительных СРО помечаются и пропускаются.
    pool позволяет передать свой список кандидатов (например, для повторной
    обработки); по умолчанию берутся компании, ещё не тронутые Checko.
    """
    if pool is None:
        pool = list(db.iter_missing_source("checko", limit=0))
    companies = select_for_checko(
        pool,
        limit=0,
        include_inactive=include_inactive,
        include_with_phones=include_with_phones,
        include_secondary=include_secondary,
        okved_prefixes=okved_prefixes,
    )
    plan = min(limit, len(companies)) if limit else len(companies)
    print(f"[checko] к обработке: {plan} (лимит бесплатного тарифа ~100/сутки; "
          "запускайте ежедневно — обработанные повторно не запрашиваются)")
    processed: list[str] = []
    skipped_sro = 0
    for company in companies:
        if limit and len(processed) >= limit:
            break
        inn = company["inn"]
        name = company.get("name_short") or company.get("name") or ""
        if sro_precheck and "sro" not in company["sources"]:
            membership = sro.check_membership(inn, session)
            if membership is not None:
                db.upsert({"inn": inn, "sources": ["sro"], **membership})
                time.sleep(config.DEFAULT_DELAY_SRO)
                if membership["sro_member"] == 1:
                    skipped_sro += 1
                    print(f"[sro]    {inn} {name}: член строительной СРО — пропускаю, "
                          "квота не тратится", flush=True)
                    continue
        try:
            data = checko.fetch(inn, api_key, session)
        except requests.RequestException as exc:
            print(f"[checko] {inn}: ошибка ({exc}), останавливаюсь — проверьте ключ/лимит")
            break
        update: dict = {"inn": inn, "sources": ["checko"]}
        if data:
            update.update(checko.extract_contacts(data))
        db.upsert(update)
        processed.append(inn)
        print(f"[checko] {len(processed)}/{plan} {inn} {name}: "
              f"телефонов {len(update.get('phones') or [])}, "
              f"e-mail {len(update.get('emails') or [])}", flush=True)
        time.sleep(delay)
    if skipped_sro:
        print(f"[checko] пропущено членов строительных СРО: {skipped_sro} (квота не потрачена)")
    print(f"[checko] готово: обработано {len(processed)}")
    return processed


def _write_membership_report(
    path: str, db: CompanyDB, inns: list[str],
    member_field: str, info_field: str, tag: str, label: str,
) -> None:
    """Результат проверки СРО/НОПРИЗ по конкретному списку ИНН — отдельным
    файлом (ИНН, название, вердикт), а не в общей выгрузке лидов."""
    rows = []
    for inn in inns:
        company = db.get(inn)
        if company is None:
            rows.append((inn, "", "не найдено в базе"))
            continue
        name = company.get("name_short") or company.get("name") or ""
        member = company.get(member_field)
        info = company.get(info_field) or []
        if member == 1:
            verdict = info[0] if info else f"член {label}"
        elif member == 0:
            verdict = info[0] if info else f"не в {label}"
        else:
            verdict = "не проверено (ошибка сети при обработке)"
        rows.append((inn, name, verdict))

    out_path = Path(path)
    if out_path.suffix.lower() == ".xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = label
        ws.append(["ИНН", "Название", "Результат"])
        for row in rows:
            ws.append(row)
        ws.freeze_panes = "A2"
        wb.save(out_path)
    else:
        import csv
        with open(out_path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(["ИНН", "Название", "Результат"])
            writer.writerows(rows)
    print(f"[{tag}] результат по списку сохранён: {out_path} ({len(rows)} строк)")


def cmd_enrich_sro(args) -> int:
    """Бесплатно помечает по реестру НОСТРОЙ, кто уже в строительной СРО."""
    session = make_session()
    processed = members = errors = 0
    file_inns: list[str] | None = None
    with CompanyDB(args.db) as db:
        if args.file:
            path = Path(args.file)
            if not path.exists():
                print(f"Файл {path} не найден.", file=sys.stderr)
                return 1
            inns: list[str] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                inn = line.strip()
                if not inn or not inn.isdigit():
                    continue
                if db.get(inn) is None:
                    # Отсутствующих в базе добавляем сами — как import-inn
                    db.upsert({"inn": inn, "kind": "ЮЛ", "sources": ["manual"]})
                inns.append(inn)
            file_inns = inns
            all_from_file = [db.get(inn) for inn in inns]
            # По умолчанию пропускаем уже проверенных — иначе на большом
            # файле повторный запуск после обрыва передопрашивал бы всех
            # заново. --recheck снимает это ограничение (перепроверка)
            if args.recheck:
                companies = all_from_file
            else:
                companies = [c for c in all_from_file if "sro" not in c["sources"]]
                skipped = len(all_from_file) - len(companies)
                if skipped:
                    print(f"[sro] уже проверено ранее (пропускаю): {skipped}")
            print(f"[sro] к проверке из файла {path}: {len(companies)} "
                  "(бесплатно, вне зависимости от лимита)")
        elif args.recheck:
            companies = [
                c for c in db.iter_all()
                if "sro" in c["sources"] and c.get("sro_member") != 1
            ]
            # Сначала рабочие пачки Checko — они уже в выгрузках
            companies.sort(key=lambda c: 0 if "checko" in c["sources"] else 1)
            if args.limit:
                companies = companies[: args.limit]
            print(f"[sro] перепроверка ранее помеченных «не в СРО»: {len(companies)}")
        else:
            companies = list(db.iter_missing_source("sro", limit=args.limit))
            print(f"[sro] к проверке по реестру НОСТРОЙ: {len(companies)} (бесплатно)")
        for company in companies:
            membership = sro.check_membership(company["inn"], session)
            if membership is None:
                errors += 1
                if errors >= 10 and errors > processed:
                    print("[sro] реестр НОСТРОЙ недоступен — останавливаюсь; "
                          "запустите команду позже", file=sys.stderr)
                    return 1
                continue
            db.upsert({"inn": company["inn"], "sources": ["sro"], **membership})
            processed += 1
            members += membership["sro_member"]
            if membership["sro_member"] == 1:
                name = company.get("name_short") or company.get("name") or ""
                print(f"[sro] {company['inn']} {name}: ЧЛЕН СРО — исключён из выгрузок",
                      flush=True)
            if processed % 100 == 0:
                print(f"[sro] проверено {processed}, в СРО {members}", flush=True)
            time.sleep(args.delay)
        if args.out and file_inns is not None:
            _write_membership_report(
                args.out, db, file_inns, "sro_member", "sro_info", "sro", "НОСТРОЙ",
            )
    print(f"[sro] готово: проверено {processed}, из них в строительной СРО {members} "
          "(исключены из выгрузок и обзвона)")
    return 0


def cmd_enrich_nopriz(args) -> int:
    """Бесплатно помечает по реестру НОПРИЗ, кто в проектно-изыскательской СРО.

    Справочная проверка — в отличие от enrich-sro, не влияет на выгрузки и
    --exclude-risky, только заполняет nopriz_member/nopriz_info.
    """
    session = make_session()
    processed = members = errors = 0
    file_inns: list[str] | None = None
    with CompanyDB(args.db) as db:
        if args.file:
            path = Path(args.file)
            if not path.exists():
                print(f"Файл {path} не найден.", file=sys.stderr)
                return 1
            inns: list[str] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                inn = line.strip()
                if not inn or not inn.isdigit():
                    continue
                if db.get(inn) is None:
                    db.upsert({"inn": inn, "kind": "ЮЛ", "sources": ["manual"]})
                inns.append(inn)
            file_inns = inns
            all_from_file = [db.get(inn) for inn in inns]
            if args.recheck:
                companies = all_from_file
            else:
                companies = [c for c in all_from_file if "nopriz" not in c["sources"]]
                skipped = len(all_from_file) - len(companies)
                if skipped:
                    print(f"[nopriz] уже проверено ранее (пропускаю): {skipped}")
            print(f"[nopriz] к проверке из файла {path}: {len(companies)} "
                  "(бесплатно, вне зависимости от лимита)")
        elif args.recheck:
            companies = [
                c for c in db.iter_all()
                if "nopriz" in c["sources"] and c.get("nopriz_member") != 1
            ]
            if args.limit:
                companies = companies[: args.limit]
            print(f"[nopriz] перепроверка ранее помеченных «не в НОПРИЗ»: {len(companies)}")
        else:
            companies = list(db.iter_missing_source("nopriz", limit=args.limit))
            print(f"[nopriz] к проверке по реестру НОПРИЗ: {len(companies)} (бесплатно)")
        for company in companies:
            membership = nopriz.check_membership(company["inn"], session)
            if membership is None:
                errors += 1
                if errors >= 10 and errors > processed:
                    print("[nopriz] реестр НОПРИЗ недоступен — останавливаюсь; "
                          "запустите команду позже", file=sys.stderr)
                    return 1
                continue
            db.upsert({"inn": company["inn"], "sources": ["nopriz"], **membership})
            processed += 1
            members += membership["nopriz_member"]
            if membership["nopriz_member"] == 1:
                name = company.get("name_short") or company.get("name") or ""
                print(f"[nopriz] {company['inn']} {name}: член проектно-изыскательской СРО",
                      flush=True)
            if processed % 100 == 0:
                print(f"[nopriz] проверено {processed}, в НОПРИЗ {members}", flush=True)
            time.sleep(args.delay)
        if args.out and file_inns is not None:
            _write_membership_report(
                args.out, db, file_inns, "nopriz_member", "nopriz_info", "nopriz", "НОПРИЗ",
            )
    print(f"[nopriz] готово: проверено {processed}, из них в НОПРИЗ {members} "
          "(справочно — из выгрузок не исключаются)")
    return 0


def cmd_enrich_checko(args) -> int:
    api_key = args.key or os.environ.get(config.CHECKO_API_KEY_ENV)
    if not api_key:
        print(f"Нужен API-ключ Checko: --key или переменная {config.CHECKO_API_KEY_ENV}. "
              "Бесплатный ключ: https://checko.ru/integration/api", file=sys.stderr)
        return 1
    session = make_session()
    with CompanyDB(args.db) as db:
        pool = None
        include_with_phones = args.include_with_phones
        include_secondary = args.include_secondary
        if args.redo_empty:
            pool = [
                c for c in db.iter_all()
                if "checko" in c["sources"] and not c["phones"] and not c["emails"]
            ]
            include_secondary = True  # уже обработанных не отбрасываем по ОКВЭД
            print(f"[checko] повторная обработка: {len(pool)} компаний без контактов")
        elif args.redo_no_director:
            pool = [
                c for c in db.iter_all()
                if "checko" in c["sources"] and not c.get("director")
                and (c["phones"] or c["emails"])
            ]
            include_with_phones = True  # у этих компаний телефоны уже есть
            include_secondary = True
            print(f"[checko] дозапрос руководителей: {len(pool)} компаний")
        elif args.redo_no_liveness:
            # bankruptcy заполняется при каждом запросе (блок ЕФРСБ приходит
            # всегда), поэтому его отсутствие = живость ещё не запрашивалась
            pool = [
                c for c in db.iter_all()
                if "checko" in c["sources"] and c.get("bankruptcy") is None
            ]
            include_with_phones = True
            include_secondary = True
            print(f"[checko] дозапрос признаков живости: {len(pool)} компаний")
        run_checko_batch(
            db, session, api_key, args.limit, args.delay,
            include_inactive=args.include_inactive,
            include_with_phones=include_with_phones,
            pool=pool,
            include_secondary=include_secondary,
            okved_prefixes=tuple(args.okved),
        )
    return 0


def todays_checko_inns(db: CompanyDB, today: str) -> set[str]:
    """ИНН компаний, которых Checko коснулся сегодня — за все запуски дня,
    а не только за текущий (нужно, чтобы daily с разными ключами Checko в
    один день не терял предыдущую пачку при пересборке файла)."""
    return {
        c["inn"] for c in db.iter_all()
        if "checko" in c["sources"] and (c.get("updated_at") or "").startswith(today)
    }


def cmd_daily(args) -> int:
    """Ежедневный прогон: Checko-пачка → добор с сайтов → Excel за сегодня."""
    from datetime import date

    api_key = args.key or os.environ.get(config.CHECKO_API_KEY_ENV)
    session = make_session()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    with CompanyDB(args.db) as db:
        processed: list[str] = []
        if api_key:
            processed = run_checko_batch(
                db, session, api_key, args.limit, args.delay,
                include_secondary=args.include_secondary,
                okved_prefixes=tuple(args.okved),
            )
        else:
            print(f"[daily] переменная {config.CHECKO_API_KEY_ENV} не задана — "
                  "шаг Checko пропущен, телефоны не приедут", file=sys.stderr)

        # Добираем контакты с сайтов, которые дал Checko в сегодняшней пачке
        sites = [
            inn for inn in processed
            if (c := db.get(inn))
            and (c.get("website") or "").strip()
            and "website" not in c["sources"]
        ]
        if sites:
            print(f"[sites] обхожу сайты сегодняшней пачки: {len(sites)}")
        site_session = make_session(retries=False)
        for idx, inn in enumerate(sites, 1):
            company = db.get(inn)
            contacts = website.harvest(company["website"], site_session,
                                       delay=config.DEFAULT_DELAY_WEBSITE)
            # Номера с сайта не смешиваются с проверенными из Checko:
            # неподтверждённые идут в отдельную колонку «проверить»
            unconfirmed = [p for p in contacts["phones"] if p not in company["phones"]]
            db.upsert({"inn": inn, "sources": ["website"],
                       "emails": contacts["emails"], "phones_site": unconfirmed})
            confirmed = len(contacts["phones"]) - len(unconfirmed)
            print(f"[sites] {idx}/{len(sites)} {company['website']}: "
                  f"подтверждено {confirmed}, на проверку +{len(unconfirmed)}, "
                  f"e-mail +{len(contacts['emails'])}", flush=True)

        def save(path: Path, **kwargs) -> tuple[Path, int]:
            try:
                return path, export_xlsx(db, path, **kwargs)
            except RuntimeError:  # нет openpyxl — падаем обратно в CSV
                csv_path = path.with_suffix(".csv")
                return csv_path, export_csv(db, csv_path, **kwargs)
            except PermissionError:
                # Файл открыт в Excel — пишем рядом, ничего не теряя
                alt = path.with_name(path.stem + "_новый" + path.suffix)
                print(f"[daily] файл {path} открыт в Excel — сохраняю как {alt}")
                return alt, export_xlsx(db, alt, **kwargs)

        exclude_risky = not args.include_risky
        if not exclude_risky:
            print("[daily] фильтр риска ОТКЛЮЧЁН (--include-risky) — в выгрузку "
                  "попадут и подозрительные компании")

        def _report_risk(stats: dict) -> None:
            # Считаем долю отсеянных только среди реальных кандидатов этого
            # конкретного файла, а не по всей истории базы — иначе цифра
            # тонет в необогащённых компаниях и выглядит как «99% мусора»
            if exclude_risky and stats:
                print(f"[daily] фильтр риска: отсеяно {stats.get('excluded', 0)}/"
                      f"{stats.get('candidates', 0)} кандидатов этого файла "
                      "(check-risk <ИНН> — разбор по одной компании)")

        todays_inns = todays_checko_inns(db, today)
        if todays_inns:
            risk_stats: dict = {}
            path, n = save(
                out_dir / f"companies_{today}.xlsx",
                only_active=False, with_contacts_only=False, inns=todays_inns,
                exclude_risky=exclude_risky, risk_stats=risk_stats,
            )
            print(f"[daily] сегодняшняя пачка (за все запуски сегодня): {path} ({n} компаний)")
            _report_risk(risk_stats)
        else:
            print("[daily] сегодня новых компаний из Checko нет "
                  "(всё уже обработано, нет ключа или исчерпан лимит)")

        risk_stats_all: dict = {}
        path, n = save(
            out_dir / "companies_all.xlsx",
            only_active=True, with_contacts_only=True, exclude_risky=exclude_risky,
            risk_stats=risk_stats_all,
        )
        print(f"[daily] полная база с контактами: {path} ({n} компаний)")
        _report_risk(risk_stats_all)
    return 0


def cmd_enrich_sites(args) -> int:
    session = make_session(retries=False)
    processed = found = 0
    with CompanyDB(args.db) as db:
        companies = [
            c for c in db.iter_missing_source("website", limit=0)
            if (c.get("website") or "").strip()
        ]
        if args.limit:
            companies = companies[: args.limit]
        print(f"[sites] сайтов к обходу: {len(companies)}")
        for company in companies:
            contacts = website.harvest(company["website"], session, delay=args.delay)
            unconfirmed = [p for p in contacts["phones"] if p not in company["phones"]]
            db.upsert({"inn": company["inn"], "sources": ["website"],
                       "emails": contacts["emails"], "phones_site": unconfirmed})
            processed += 1
            if contacts["emails"] or contacts["phones"]:
                found += 1
            if processed % 20 == 0:
                print(f"[sites] обработано {processed}, с контактами {found}")
    print(f"[sites] готово: обработано {processed}, контакты найдены у {found}")
    return 0


def cmd_export(args) -> int:
    if not args.csv and not args.xlsx:
        print("Укажите --csv и/или --xlsx.", file=sys.stderr)
        return 1
    with CompanyDB(args.db) as db:
        def _report_risk(stats: dict) -> None:
            # Доля отсеянных считается только среди кандидатов ЭТОЙ выгрузки
            # (уже прошедших --only-active/--with-contacts-only/--alive-only),
            # а не по всей базе — иначе необогащённые компании тонут в цифре
            if args.exclude_risky and stats:
                print(f"[export] фильтр риска: отсеяно {stats.get('excluded', 0)}/"
                      f"{stats.get('candidates', 0)} кандидатов этой выгрузки "
                      "(check-risk <ИНН> — разбор по одной компании)")

        try:
            if args.csv:
                risk_stats: dict = {}
                n = export_csv(db, args.csv, args.only_active, args.with_contacts_only,
                               include_sro=args.include_sro, alive_only=args.alive_only,
                               exclude_risky=args.exclude_risky, risk_stats=risk_stats)
                print(f"[export] CSV: {args.csv} ({n} строк)")
                _report_risk(risk_stats)
            if args.xlsx:
                risk_stats = {}
                n = export_xlsx(db, args.xlsx, args.only_active, args.with_contacts_only,
                                include_sro=args.include_sro, alive_only=args.alive_only,
                                exclude_risky=args.exclude_risky, risk_stats=risk_stats)
                print(f"[export] XLSX: {args.xlsx} ({n} строк)")
                _report_risk(risk_stats)
        except PermissionError:
            print("Не удалось записать файл: он открыт в Excel. "
                  "Закройте его и повторите команду.", file=sys.stderr)
            return 1
    return 0


def cmd_clean_phones(args) -> int:
    """Чистит телефоны: удаляет невалидные, пересобирает подозрительно длинные."""
    from collections import Counter

    from .normalize import is_valid_phone

    session = make_session(retries=False)
    removed = touched = 0
    flagged: list[dict] = []
    counter: Counter = Counter()
    with CompanyDB(args.db) as db:
        for company in db.iter_all():
            changed = False
            for field in ("phones", "phones_site"):
                values = company.get(field) or []
                valid = [p for p in values if is_valid_phone(p)]
                if len(valid) != len(values):
                    db.replace_list(company["inn"], field, valid)
                    removed += len(values) - len(valid)
                    changed = True
                    company[field] = valid
            if changed:
                touched += 1
            total_now = len(company["phones"]) + len(company.get("phones_site") or [])
            for p in (*company["phones"], *(company.get("phones_site") or [])):
                counter[p] += 1
            if args.reharvest_over and total_now > args.reharvest_over:
                flagged.append(company)
        print(f"[clean] удалено номеров с несуществующими кодами: {removed} "
              f"(у {touched} компаний)")

        for company in flagged:
            inn = company["inn"]
            name = company.get("name_short") or company.get("name") or ""
            total = len(company["phones"]) + len(company.get("phones_site") or [])
            site = (company.get("website") or "").strip()
            if not site:
                print(f"[clean] {inn} {name}: {total} номеров, "
                      "сайт неизвестен — проверьте вручную")
                continue
            # Аномально длинный список — наследие старого сборщика: телефоны
            # пересобираются с сайта в колонку «проверить», основная очищается
            # (официальные номера вернутся при следующем enrich-checko --redo-empty)
            contacts = website.harvest(site, session, delay=args.delay)
            fresh = [p for p in contacts["phones"] if is_valid_phone(p)]
            db.replace_list(inn, "phones_site", fresh)
            db.replace_list(inn, "phones", [])
            print(f"[clean] {inn} {name}: пересобрано с сайта {site} — "
                  f"было {total}, на проверку {len(fresh)}", flush=True)

        shared = {p: c for p, c in counter.items() if c >= 3}
        if shared:
            print("\n[clean] номера, встречающиеся у 3+ компаний (возможен "
                  "колл-центр или мусор — проверьте вручную):")
            for phone, count in sorted(shared.items(), key=lambda x: -x[1]):
                print(f"  {phone} — у {count} компаний")
    return 0


def cmd_check_sro(args) -> int:
    """Проверяет один ИНН по реестру НОСТРОЙ с подбором формата фильтра."""
    import json as _json

    session = make_session()
    sro._working_body = None
    sro._format_unusable = False
    result = sro.check_membership(args.inn, session)
    if result is None:
        print("Не удалось определить членство: реестр недоступен или ни один "
              "формат фильтра не сработал. Ниже — сырой ответ для отладки.")
        payload = sro._post(sro._FILTER_BODIES[0](args.inn), session, 30)
        if payload is not None:
            text = _json.dumps(payload, ensure_ascii=False)
            print(f"\nСырой ответ формата №1 ({len(text)} символов):\n{text[:1200]}")
        return 1
    if result["sro_member"] == 1:
        print(f"ИНН {args.inn}: ЧЛЕН строительной СРО (будет отсечён)")
    elif result["sro_info"]:
        print(f"ИНН {args.inn}: {result['sro_info'][0]} (НЕ отсекается)")
    else:
        print(f"ИНН {args.inn}: записей по этому ИНН не найдено (не в СРО)")
    if sro._working_body is not None:
        print(f"[диагностика] сработал формат фильтра №{sro._working_body + 1}")
    return 0


def cmd_check_nopriz(args) -> int:
    """Проверяет один ИНН по реестру НОПРИЗ с подбором формата фильтра."""
    import json as _json

    session = make_session()
    nopriz._working_body = None
    nopriz._format_unusable = False
    result = nopriz.check_membership(args.inn, session)
    if result is None:
        print("Не удалось определить членство: реестр недоступен или ни один "
              "формат фильтра не сработал. Ниже — сырой ответ для отладки.")
        payload = nopriz._post(nopriz._FILTER_BODIES[0](args.inn), session, 30)
        if payload is not None:
            text = _json.dumps(payload, ensure_ascii=False)
            print(f"\nСырой ответ формата №1 ({len(text)} символов):\n{text[:1200]}")
        return 1
    if result["nopriz_member"] == 1:
        print(f"ИНН {args.inn}: член проектно-изыскательской СРО (НОПРИЗ)")
    elif result["nopriz_info"]:
        print(f"ИНН {args.inn}: {result['nopriz_info'][0]}")
    else:
        print(f"ИНН {args.inn}: записей по этому ИНН не найдено (не в НОПРИЗ)")
    if nopriz._working_body is not None:
        print(f"[диагностика] сработал формат фильтра №{nopriz._working_body + 1}")
    return 0


def cmd_check_checko(args) -> int:
    """Показывает сырой ответ Checko API и что из него извлекает программа."""
    import json as _json

    api_key = args.key or os.environ.get(config.CHECKO_API_KEY_ENV)
    if not api_key:
        print(f"Нужен API-ключ: --key или переменная {config.CHECKO_API_KEY_ENV}.", file=sys.stderr)
        return 1
    session = make_session()
    resp = session.get(
        config.CHECKO_COMPANY_URL, params={"key": api_key, "inn": args.inn}, timeout=30
    )
    print(f"HTTP-статус: {resp.status_code}")
    text = resp.text
    try:
        payload = resp.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        info = checko.extract_contacts(payload["data"])
        print(f"Извлечено программой: телефоны {info['phones']}, "
              f"e-mail {info['emails']}, сайт {info['website']}")
        text = _json.dumps(payload, ensure_ascii=False)
    lowered = text.lower()
    print("\nПризнаки контактов в ответе:")
    for marker in ("контакт", "тел", "емэйл", "емейл", "email", "почта", "сайт"):
        print(f"  «{marker}»: {'есть' if marker in lowered else 'нет'}")
    print(f"\nСырой ответ целиком ({len(text)} символов):")
    print(text[:20000])
    return 0


def cmd_check_risk(args) -> int:
    """Показывает разбор скоринга риска (тот же, что и --exclude-risky) по одному ИНН."""
    with CompanyDB(args.db) as db:
        company = db.get(args.inn)
        if company is None:
            print(f"ИНН {args.inn} не найден в базе.", file=sys.stderr)
            return 1
        companies = list(db.iter_all())
        scores = riskscore.score_all(companies)
        score, reasons = scores[args.inn]
    name = company.get("name_short") or company.get("name") or ""
    verdict = (
        "МУСОР" if score >= riskscore.JUNK_THRESHOLD
        else "ПОД ВОПРОСОМ" if score >= riskscore.CHECK_THRESHOLD
        else "ЧИСТЫЙ"
    )
    print(f"ИНН {args.inn} {name}: скор {score} — {verdict}")
    for reason in reasons:
        print(f"  - {reason}")
    if not reasons:
        print("  - причин для снижения оценки не найдено")
    return 0


def cmd_stats(args) -> int:
    with CompanyDB(args.db) as db:
        for key, value in db.stats().items():
            print(f"{key:28} {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
