"""CLI — основной интерфейс приложения.

Пример:
    python finder.py --input companies.xlsx --output result.xlsx \
                     --sources all --threads 10 --depth full
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from connectors import CONNECTOR_REGISTRY
from core.config import Config
from core.models import CompanyStatus
from core.orchestrator import Orchestrator, Progress
from storage.db import Database
from utils.io_input import read_companies, write_errors_xlsx
from utils.io_output import export_results
from utils.logging_setup import setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="finder",
        description="Массовый поиск и обогащение контактов юрлиц РФ по открытым источникам",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", "-i", help="входной файл (XLSX/CSV/TXT)")
    parser.add_argument("--output", "-o", default="result.xlsx",
                        help="итоговый XLSX")
    parser.add_argument("--errors-file", default="errors.xlsx",
                        help="файл отбраковки входных строк")
    parser.add_argument("--sources", default="all",
                        help="источники через запятую или all "
                             f"(доступны: {', '.join(sorted(CONNECTOR_REGISTRY))})")
    parser.add_argument("--threads", type=int, default=None,
                        help="одновременно обрабатываемых компаний "
                             "(по умолчанию http.concurrency из config.yaml)")
    parser.add_argument("--depth", choices=("full", "first_email"), default=None,
                        help="full — опросить всё; first_email — до первого e-mail")
    parser.add_argument("--config", default=None, help="путь к config.yaml")
    parser.add_argument("--db", default=None,
                        help="путь к SQLite-базе (по умолчанию из config.yaml)")
    parser.add_argument("--fresh", action="store_true",
                        help="сбросить прогресс и собрать всё заново (кэш HTTP остаётся)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="подробный лог в консоль")
    return parser


def parse_sources(value: str) -> Optional[set[str]]:
    value = (value or "all").strip().lower()
    if value in ("all", "*", ""):
        return None
    requested = {s.strip() for s in value.split(",") if s.strip()}
    unknown = requested - set(CONNECTOR_REGISTRY)
    if unknown:
        raise SystemExit(
            f"Неизвестные источники: {', '.join(sorted(unknown))}. "
            f"Доступны: {', '.join(sorted(CONNECTOR_REGISTRY))}")
    return requested


def _print_progress(progress: Progress, message: str) -> None:
    eta = progress.eta_seconds
    eta_text = f", ETA {int(eta // 60)}:{int(eta % 60):02d}" if eta else ""
    sys.stdout.write(
        f"\r[{progress.processed}/{progress.total}] "
        f"e-mail: {progress.found_email}, тел.: {progress.found_phone}, "
        f"ошибок: {progress.errors}{eta_text}   ")
    sys.stdout.flush()


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    config = Config.load(args.config)
    logger = setup_logging(config.resolve_path(config.get("output.logs_dir", "logs")),
                           verbose=args.verbose)

    db_path = Path(args.db) if args.db else config.db_path
    db = Database(db_path)
    logger.info("База: %s", db_path)

    # --- входной файл --------------------------------------------------
    if args.input:
        result = read_companies(args.input)
        new = sum(1 for c in result.companies if db.upsert_company_input(c))
        logger.info(
            "Вход: %d компаний (%d новых), %d дублей отброшено, %d строк в браке",
            len(result.companies), new, result.duplicates, len(result.errors))
        if result.errors:
            write_errors_xlsx(result.errors, args.errors_file)
            logger.info("Брак сохранён: %s", args.errors_file)

    if args.fresh:
        db.reset_all_pending()
        logger.info("Статусы сброшены (--fresh): пересобираем всё")

    counts = db.status_counts()
    pending = counts.get("pending", 0) + counts.get("retry_later", 0)
    if pending == 0 and not counts:
        logger.error("В базе нет компаний. Укажите входной файл: --input companies.xlsx")
        return 2
    logger.info("Очередь: %s", counts)

    # --- прогон --------------------------------------------------------
    if pending:
        orchestrator = Orchestrator(
            config, db,
            only_sources=parse_sources(args.sources),
            concurrency=args.threads,
            depth=args.depth,
        )
        orchestrator.on_progress(_print_progress)
        try:
            asyncio.run(orchestrator.run())
            print()
        except KeyboardInterrupt:
            print("\nОстановлено пользователем. Прогресс сохранён — "
                  "повторный запуск продолжит с места остановки.")
    else:
        logger.info("Все компании уже обработаны — только экспорт "
                    "(для пересбора используйте --fresh)")

    # --- экспорт -------------------------------------------------------
    stats = export_results(db, args.output)
    logger.info(
        "Готово: %s | всего %d, полностью %d, частично %d, не найдено %d",
        args.output, stats["total"], stats["full"], stats["partial"], stats["none"])

    unavailable = db.unavailable_sources()
    if unavailable:
        logger.info("Недоступные источники: %s",
                    "; ".join(f"{u['source']} ({u.get('note') or 'без деталей'})"
                              for u in unavailable))
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
