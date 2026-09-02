#!/usr/bin/env python3
"""sro-leads: оркестратор. collect -> score -> enrich -> export.

  python run.py --full                    # всё подряд (то же, что без флагов)
  python run.py --only nostroy_registry   # прогнать один коллектор (+ скоринг и экспорт)
  python run.py --only nostroy_registry --backfill 90   # исторические исключения за 90 дней из самих записей
  python run.py --no-enrich               # собрать без обогащения
  python run.py --export-only             # только пересобрать Excel из БД
  python run.py --mark 7814858513 called "перезвонить в четверг"   # статус обзвона
  python run.py --check-api nostroy       # один запрос к API и сверка карты полей, в БД не пишет
  python run.py --snapshot-report nostroy  # что за статусы и даты в снапшоте, применим ли backfill
  python run.py --inspect 7814858513      # карточка организации для сверки с реестром глазами
  python run.py --inspect-top 10 --out inspect.txt   # то же по десятке самых горячих, в файл
  python run.py --drop-snapshot nostroy --date 2026-09-02   # удалить снапшот за дату, чтобы снять заново
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.db import Database  # noqa: E402
from core.enrich import Enricher  # noqa: E402
from core.export import build_export
from core.report import inspect_orgs, snapshot_report, top_inns  # noqa: E402
from core.models import OUTREACH_STATUSES  # noqa: E402
from core.scoring import rescore_all  # noqa: E402
from core.utils import HttpClient, load_config, resolve_path, setup_logging  # noqa: E402
from collectors import discover  # noqa: E402

log = logging.getLogger("sro_leads")


def run_collectors(cfg: dict, db: Database, names: list[str], backfill_days: int | None = None) -> dict[str, int]:
    available = discover()
    http = HttpClient(cfg.get("http", {}))
    results: dict[str, int] = {}
    for name in names:
        cls = available.get(name)
        if cls is None:
            log.error("Коллектор «%s» не найден. Доступны: %s", name, ", ".join(sorted(available)))
            results[name] = -1
            continue
        started = time.monotonic()
        log.info("=== %s: старт ===", name)
        collector = cls(cfg, db, http)
        collector.backfill_days = backfill_days
        try:
            signals = collector.collect()
            if collector.snapshot is not None:
                snap = collector.snapshot
                n = db.write_snapshot(snap.source, snap.snapshot_date, snap.rows)
                db.write_snapshot_meta(snap.source, snap.snapshot_date, snap.meta)
                log.info("%s: снапшот %s записан, строк %d (%s)", name, snap.snapshot_date, n, snap.meta.describe())
            added = db.add_signals(signals)
            db.commit()
            collector.finalize()
            results[name] = added
            log.info("=== %s: готово за %.0f с, сигналов %d, из них новых %d ===",
                     name, time.monotonic() - started, len(signals), added)
        except Exception:
            db.rollback()
            results[name] = -1
            log.exception("=== %s: ОШИБКА, коллектор пропущен, остальные продолжают ===", name)
    return results


def drop_snapshot(cfg: dict, db: Database, source: str, date: Optional[str]) -> int:
    """Удалить снапшот за дату, чтобы снять его заново без ручного SQL."""
    dates = db.snapshot_dates(source)
    if not dates:
        print(f"Снапшотов источника «{source}» в базе нет.")
        return 2
    date = date or dates[0]
    if date not in dates:
        print(f"Снапшота {source} за {date} нет. Есть: {', '.join(dates[:10])}")
        return 2
    meta = db.snapshot_meta(source, date)
    removed = db.drop_snapshot(source, date)
    db.commit()
    log.info("Снапшот %s за %s удалён, строк %d%s", source, date, removed,
             f" ({meta.describe()})" if meta else "")
    print(f"Снапшот {source} за {date} удалён: строк {removed}. Снимите заново: "
          f"python run.py --only {source}_registry")
    return 0


def print_snapshot_report(cfg: dict, db: Database, source: str, date: Optional[str]) -> int:
    """Отчёт по снапшоту: что за статусы и даты пришли, применим ли backfill. Только чтение."""
    ok, report = snapshot_report(db, cfg, source, date)
    print(report)
    return 0 if ok else 1


def inspect(cfg: dict, db: Database, inns: list[str], top: Optional[int], out: Optional[str]) -> int:
    """Карточки организаций для ручной сверки с реестром. Только чтение БД."""
    if top:
        inns = top_inns(db, cfg, top)
        if not inns:
            print("Лидов, подходящих под фильтры экспорта, в базе нет.")
            return 1
    report = inspect_orgs(db, cfg, inns)
    if out:
        path = Path(out)
        if not path.is_absolute():
            path = Path(cfg.get("_root", ".")) / out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report + "\n", encoding="utf-8")
        log.info("Сверка по %d организациям сохранена: %s", len(inns), path)
        print(f"Сохранено: {path} ({len(inns)} организаций)")
    else:
        print(report)
    return 0


def check_api(cfg: dict, source: str) -> int:
    """Диагностика живого коннектора: печатает отчёт в консоль, БД не трогает."""
    from collectors.base import RegistryCollector

    cls = next((c for c in discover().values() if issubclass(c, RegistryCollector) and c.source == source), None)
    if cls is None:
        print(f"Нет реестрового коллектора для источника «{source}». Доступны: "
              + ", ".join(sorted(c.source for c in discover().values() if issubclass(c, RegistryCollector))))
        return 2
    collector = cls(cfg, db=None, http=HttpClient(cfg.get("http", {})))  # type: ignore[arg-type]
    tag, report = collector.check_api()
    print(report)
    return 1 if tag == "error" else 0   # warn — это предупреждение, а не отказ


def prune(cfg: dict, db: Database) -> None:
    keep = int(cfg.get("registry", {}).get("keep_days", 14))
    for source in ("nostroy", "nopriz"):
        removed = db.prune_snapshots(source, keep)
        if removed:
            log.info("Снапшоты %s: удалено старых строк %d (оставлено дат: %d)", source, removed, keep)
    db.commit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="sro-leads: сбор лидов на вступление в СРО")
    parser.add_argument("--only", metavar="NAME", help="прогнать только этот коллектор (можно несколько через запятую)")
    parser.add_argument("--no-enrich", action="store_true", help="собрать без обогащения")
    parser.add_argument("--export-only", action="store_true", help="только пересобрать Excel из БД")
    parser.add_argument("--full", action="store_true", help="всё подряд (по умолчанию)")
    parser.add_argument("--backfill", nargs="?", const=90, type=int, metavar="N",
                        help="реестры: сигналы из самих записей за последние N дней (по умолчанию 90) вместо диффа")
    parser.add_argument("--mark", nargs="+", metavar=("INN", "STATUS"),
                        help=f"статус обзвона: INN STATUS [комментарий]; статусы: {', '.join(OUTREACH_STATUSES)}")
    parser.add_argument("--drop-snapshot", metavar="SOURCE", help="удалить снапшот источника (nostroy | nopriz) "
                        "за дату --date (по умолчанию последний), чтобы снять его заново")
    parser.add_argument("--date", metavar="YYYY-MM-DD", help="дата снапшота для --drop-snapshot и --snapshot-report")
    parser.add_argument("--snapshot-report", metavar="SOURCE", help="отчёт по снятому снапшоту источника "
                        "(nostroy | nopriz) за --date (по умолчанию последний): статусы, даты, применим ли backfill")
    parser.add_argument("--inspect", nargs="+", metavar="INN", help="карточки организаций по ИНН "
                        "для ручной сверки с реестром: сигналы, записи снапшота, ссылки, контакты")
    parser.add_argument("--inspect-top", type=int, metavar="N", help="то же для N организаций с верха "
                        "листа «Горячие» (те же фильтры, что и экспорт)")
    parser.add_argument("--out", metavar="FILE", help="сохранить вывод --inspect в файл")
    parser.add_argument("--check-api", metavar="SOURCE", help="один запрос к API реестра (nostroy | nopriz) "
                        "и сверка карты полей; в БД ничего не пишет")
    parser.add_argument("--config", help="путь к config.yaml")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    setup_logging(resolve_path(cfg, "logs_dir", "logs"))
    if args.check_api:
        return check_api(cfg, args.check_api)
    db = Database(resolve_path(cfg, "db", "data/sro_leads.db"))
    started = time.monotonic()
    try:
        if args.inspect or args.inspect_top:
            return inspect(cfg, db, args.inspect or [], args.inspect_top, args.out)

        if args.snapshot_report:
            return print_snapshot_report(cfg, db, args.snapshot_report, args.date)

        if args.drop_snapshot:
            return drop_snapshot(cfg, db, args.drop_snapshot, args.date)

        if args.mark:
            if len(args.mark) < 2 or args.mark[1] not in OUTREACH_STATUSES:
                parser.error(f"--mark INN STATUS [комментарий]; статусы: {', '.join(OUTREACH_STATUSES)}")
            inn, status = args.mark[0], args.mark[1]
            note = " ".join(args.mark[2:]) or None
            db.set_outreach(inn, status, note)
            db.commit()
            log.info("Обзвон: %s -> %s%s", inn, status, f" ({note})" if note else "")
            return 0

        if not args.export_only:
            names = [n.strip() for n in args.only.split(",")] if args.only else list(
                cfg.get("collectors", {}).get("enabled", []))
            results = run_collectors(cfg, db, names, args.backfill)
            prune(cfg, db)
            scores = rescore_all(cfg=cfg, db=db)
            log.info("Скоринг: организаций %d, приоритет 1: %d, приоритет 2: %d",
                     len(scores), sum(1 for r in scores.values() if r.priority == 1),
                     sum(1 for r in scores.values() if r.priority == 2))
            if not args.no_enrich:
                stats = Enricher(cfg, db).run()
                log.info("Обогащение: %s", stats)
            log.info("Коллекторы: %s", results)

        path = build_export(db, cfg)
        log.info("Готово за %.0f с. Файл: %s. БД: %s", time.monotonic() - started, path, db.stats())
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
