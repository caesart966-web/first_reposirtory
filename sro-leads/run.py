#!/usr/bin/env python3
"""sro-leads: оркестратор. collect -> score -> enrich -> export.

  python run.py --full                    # всё подряд (то же, что без флагов)
  python run.py --only nostroy_registry   # прогнать один коллектор (+ скоринг и экспорт)
  python run.py --only nostroy_registry --backfill 90   # исторические исключения за 90 дней из самих записей
  python run.py --no-enrich               # собрать без обогащения
  python run.py --export-only             # только пересобрать Excel из БД
  python run.py --mark 7814858513 called "перезвонить в четверг"   # статус обзвона
  python run.py --check-api nostroy       # один запрос к API и сверка карты полей, в БД не пишет
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.db import Database  # noqa: E402
from core.enrich import Enricher  # noqa: E402
from core.export import build_export  # noqa: E402
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
                n = db.write_snapshot(collector.snapshot.source, collector.snapshot.snapshot_date,
                                      collector.snapshot.rows)
                log.info("%s: снапшот %s записан, строк %d", name, collector.snapshot.snapshot_date, n)
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


def check_api(cfg: dict, source: str) -> int:
    """Диагностика живого коннектора: печатает отчёт в консоль, БД не трогает."""
    from collectors.base import RegistryCollector

    cls = next((c for c in discover().values() if issubclass(c, RegistryCollector) and c.source == source), None)
    if cls is None:
        print(f"Нет реестрового коллектора для источника «{source}». Доступны: "
              + ", ".join(sorted(c.source for c in discover().values() if issubclass(c, RegistryCollector))))
        return 2
    collector = cls(cfg, db=None, http=HttpClient(cfg.get("http", {})))  # type: ignore[arg-type]
    ok, report = collector.check_api()
    print(report)
    return 0 if ok else 1


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
