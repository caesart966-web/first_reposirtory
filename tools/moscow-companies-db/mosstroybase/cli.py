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

from . import config
from .db import CompanyDB
from .export import export_csv, export_xlsx
from .http import make_session
from .sources import checko, egrul, rsmp, sro, website


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
    p.set_defaults(func=cmd_enrich_checko)

    p = add_parser("enrich-sites", help="собрать контакты с сайтов компаний (где сайт известен)")
    p.add_argument("--limit", type=int, default=0, help="обработать не более N компаний")
    p.add_argument("--delay", type=float, default=config.DEFAULT_DELAY_WEBSITE, help="пауза, сек")
    p.set_defaults(func=cmd_enrich_sites)

    p = add_parser("enrich-sro", help="пометить членов строительных СРО по реестру НОСТРОЙ (бесплатно)")
    p.add_argument("--limit", type=int, default=0, help="проверить не более N компаний")
    p.add_argument("--delay", type=float, default=config.DEFAULT_DELAY_SRO, help="пауза, сек")
    p.set_defaults(func=cmd_enrich_sro)

    p = add_parser("daily", help="ежедневный прогон: СРО-фильтр + Checko-пачка + сайты + Excel за сегодня")
    p.add_argument("--key", default=None, help=f"API-ключ Checko (или переменная {config.CHECKO_API_KEY_ENV})")
    p.add_argument("--limit", type=int, default=100, help="размер дневной пачки (по умолчанию 100)")
    p.add_argument("--delay", type=float, default=config.DEFAULT_DELAY_CHECKO, help="пауза, сек")
    p.add_argument("--out-dir", default="exports", help="папка для Excel-файлов (по умолчанию exports/)")
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
    p.set_defaults(func=cmd_export)

    p = add_parser("check-sro", help="диагностика: проверить один ИНН по реестру НОСТРОЙ")
    p.add_argument("inn", help="ИНН для проверки")
    p.set_defaults(func=cmd_check_sro)

    p = add_parser("check-checko", help="диагностика: сырой ответ Checko API по одному ИНН")
    p.add_argument("inn", help="ИНН для проверки")
    p.add_argument("--key", default=None, help=f"API-ключ (или переменная {config.CHECKO_API_KEY_ENV})")
    p.set_defaults(func=cmd_check_checko)

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
                    print("[egrul] слишком много ошибок подряд — похоже, источник "
                          "недоступен; останавливаюсь", file=sys.stderr)
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
) -> list[dict]:
    """Отбирает компании под квоту Checko: без лишней траты запросов.

    По умолчанию пропускаем ликвидированные и уже имеющие телефон; члены
    строительных СРО не берутся никогда. В первую очередь — компании,
    у которых строительный ОКВЭД основной (а не доп.).
    """
    candidates = []
    for company in companies:
        if company.get("sro_member") == 1:
            continue
        if not include_inactive and company.get("is_active") == 0:
            continue
        if not include_with_phones and company.get("phones"):
            continue
        candidates.append(company)
    # Сначала основной строительный ОКВЭД; внутри — сначала средние и малые:
    # у них телефоны в источниках Checko находятся заметно чаще, чем у микро
    msp_priority = {"среднее": 0, "малое": 1, "микро": 2}
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


def cmd_enrich_sro(args) -> int:
    """Бесплатно помечает по реестру НОСТРОЙ, кто уже в строительной СРО."""
    session = make_session()
    processed = members = errors = 0
    with CompanyDB(args.db) as db:
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
            if processed % 100 == 0:
                print(f"[sro] проверено {processed}, в СРО {members}")
            time.sleep(args.delay)
    print(f"[sro] готово: проверено {processed}, из них в строительной СРО {members} "
          "(исключены из выгрузок и обзвона)")
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
        if args.redo_empty:
            pool = [
                c for c in db.iter_all()
                if "checko" in c["sources"] and not c["phones"] and not c["emails"]
            ]
            print(f"[checko] повторная обработка: {len(pool)} компаний без контактов")
        run_checko_batch(
            db, session, api_key, args.limit, args.delay,
            include_inactive=args.include_inactive,
            include_with_phones=args.include_with_phones,
            pool=pool,
        )
    return 0


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
            processed = run_checko_batch(db, session, api_key, args.limit, args.delay)
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
        for idx, inn in enumerate(sites, 1):
            company = db.get(inn)
            contacts = website.harvest(company["website"], session, delay=config.DEFAULT_DELAY_WEBSITE)
            db.upsert({"inn": inn, "sources": ["website"], **contacts})
            print(f"[sites] {idx}/{len(sites)} {company['website']}: "
                  f"телефонов +{len(contacts['phones'])}, e-mail +{len(contacts['emails'])}",
                  flush=True)

        def save(path: Path, **kwargs) -> tuple[Path, int]:
            try:
                return path, export_xlsx(db, path, **kwargs)
            except RuntimeError:  # нет openpyxl — падаем обратно в CSV
                csv_path = path.with_suffix(".csv")
                return csv_path, export_csv(db, csv_path, **kwargs)

        if processed:
            path, n = save(
                out_dir / f"companies_{today}.xlsx",
                only_active=False, with_contacts_only=False, inns=set(processed),
            )
            print(f"[daily] сегодняшняя пачка: {path} ({n} компаний)")
        else:
            print("[daily] сегодня новых компаний из Checko нет "
                  "(всё уже обработано, нет ключа или исчерпан лимит)")

        path, n = save(
            out_dir / "companies_all.xlsx",
            only_active=True, with_contacts_only=True,
        )
        print(f"[daily] полная база с контактами: {path} ({n} компаний)")
    return 0


def cmd_enrich_sites(args) -> int:
    session = make_session()
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
            update = {"inn": company["inn"], "sources": ["website"], **contacts}
            db.upsert(update)
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
        if args.csv:
            n = export_csv(db, args.csv, args.only_active, args.with_contacts_only,
                           include_sro=args.include_sro)
            print(f"[export] CSV: {args.csv} ({n} строк)")
        if args.xlsx:
            n = export_xlsx(db, args.xlsx, args.only_active, args.with_contacts_only,
                            include_sro=args.include_sro)
            print(f"[export] XLSX: {args.xlsx} ({n} строк)")
    return 0


def cmd_check_sro(args) -> int:
    """Показывает сырой ответ реестра НОСТРОЙ по одному ИНН — для отладки."""
    import json as _json

    session = make_session()
    payload = sro._query(args.inn, session, 30)
    if payload is None:
        print("Реестр НОСТРОЙ не ответил (сеть или формат запроса). Попробуйте позже.")
        return 1
    verdict = sro.evaluate(payload, args.inn)
    labels = {"member": "ЧЛЕН строительной СРО (будет отсечён)",
              "former": "исключён/бывший член (НЕ отсекается)",
              None: "записей по этому ИНН не найдено (не в СРО)"}
    print(f"ИНН {args.inn}: {labels[verdict]}")
    text = _json.dumps(payload, ensure_ascii=False)
    print(f"\nОтвет реестра (первые 800 символов из {len(text)}):\n{text[:800]}")
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


def cmd_stats(args) -> int:
    with CompanyDB(args.db) as db:
        for key, value in db.stats().items():
            print(f"{key:28} {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
