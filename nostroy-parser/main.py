#!/usr/bin/env python3
"""
Парсер реестра НОСТРОЙ + сбор контактов с checko.ru.

Принимает на вход ОДИН объект — архив ``.rar``/``.zip``, отдельный Excel-файл
или папку — рекурсивно находит все таблицы, читает все листы, извлекает записи
членов СРО (название, ИНН, дата вступления, дата исключения, контакты из
реестра), после чего обогащает их контактами с checko.ru с соблюдением
суточного лимита бесплатных запросов и сохранением прогресса между днями.

Примеры запуска
---------------

    # архив с выгрузкой реестра
    python main.py --input "C:/Данные/Реестр СРО 410.rar"

    # один Excel-файл, результаты в отдельную папку
    python main.py --input ./reestr.xlsx --output ./output

    # только разбор реестра, без обращений к checko.ru
    python main.py --input ./reestr.zip --no-checko

    # продолжить на следующий день (та же команда — прогресс подхватится сам)
    python main.py --input "C:/Данные/Реестр СРО 410.rar"

Полный список ключей: ``python main.py --help``.
"""

from __future__ import annotations

import argparse
import sys
import os
from datetime import date
from pathlib import Path

# Проверяем версию до импорта пакета: он использует синтаксис Python 3.10+
# (dataclass(slots=True), аннотации вида ``str | None``).
if sys.version_info < (3, 10):
    sys.exit(
        "Требуется Python 3.10 или новее. "
        f"Установлена версия {sys.version_info.major}.{sys.version_info.minor}."
    )

from nostroy_checko import __version__
from nostroy_checko.config import (
    DEFAULT_DAILY_LIMIT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RPS,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    DEFAULT_WORKERS,
    Settings,
)
from nostroy_checko.logging_setup import setup_logging


def build_parser() -> argparse.ArgumentParser:
    """Описывает все аргументы командной строки."""
    parser = argparse.ArgumentParser(
        prog="nostroy-checko",
        description=(
            "Разбор реестра НОСТРОЙ (архив/Excel) и сбор контактов с checko.ru "
            "с учётом суточного лимита бесплатных запросов."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=(
            "Пример: python main.py --input ./Реестр.rar --output ./output --workers 4\n"
            "Прогресс сохраняется автоматически: запустите ту же команду на следующий "
            "день, и обработка продолжится с места остановки."
        ),
    )

    # ------------------------------- пути ---------------------------------- #
    group_io = parser.add_argument_group("Входные и выходные данные")
    group_io.add_argument(
        "--input", "-i",
        required=True,
        metavar="ПУТЬ",
        help="архив .rar/.zip, Excel-файл (.xlsx/.xlsm/.xls/.xlsb) или папка с файлами",
    )
    group_io.add_argument(
        "--output", "-o",
        default="output",
        metavar="ПАПКА",
        help="папка для результатов (создаётся автоматически)",
    )
    group_io.add_argument(
        "--report-date",
        default=None,
        metavar="ГГГГ-ММ-ДД",
        help="дата в имени итогового файла (по умолчанию — сегодня)",
    )

    # ---------------------------- разбор таблиц ----------------------------- #
    group_parse = parser.add_argument_group("Разбор таблиц")
    group_parse.add_argument(
        "--dedupe-by",
        choices=("inn", "name_inn"),
        default="inn",
        help=(
            "как определять уникальную компанию: inn — по ИНН (экономит квоту, "
            "рекомендуется), name_inn — по паре «название + ИНН»"
        ),
    )
    group_parse.add_argument(
        "--header-scan-rows",
        type=int, default=60, metavar="N",
        help="сколько верхних строк листа просматривать в поисках шапки",
    )
    group_parse.add_argument(
        "--header-max-span",
        type=int, default=3, metavar="N",
        help="максимальная высота «многоэтажной» шапки в строках",
    )
    group_parse.add_argument(
        "--content-sample",
        type=int, default=400, metavar="N",
        help="сколько значений колонки анализировать при автоопределении её роли",
    )

    # ------------------------------ checko.ru ------------------------------- #
    group_checko = parser.add_argument_group("Запросы к checko.ru")
    group_checko.add_argument(
        "--no-checko",
        action="store_true",
        help="не обращаться к checko.ru — только разобрать реестр",
    )
    group_checko.add_argument(
        "--checko-api-key",
        default=None, metavar="КЛЮЧ",
        help=(
            "ключ официального API checko.ru (api.checko.ru) — надёжнее разбора HTML "
            "и не блокируется защитой сайта; можно задать переменной окружения "
            "CHECKO_API_KEY. Без ключа скрипт разбирает обычные страницы сайта"
        ),
    )
    group_checko.add_argument(
        "--daily-limit",
        type=int, default=DEFAULT_DAILY_LIMIT, metavar="N",
        help="суточный лимит бесплатных запросов к checko.ru",
    )
    group_checko.add_argument(
        "--workers", "-w",
        type=int, default=DEFAULT_WORKERS, metavar="N",
        help="число параллельных потоков запросов",
    )
    group_checko.add_argument(
        "--rps",
        type=float, default=DEFAULT_RPS, metavar="ЧИСЛО",
        help="максимум запросов в секунду суммарно по всем потокам",
    )
    group_checko.add_argument(
        "--timeout",
        type=float, default=DEFAULT_TIMEOUT, metavar="СЕК",
        help="таймаут одного HTTP-запроса",
    )
    group_checko.add_argument(
        "--max-retries",
        type=int, default=DEFAULT_MAX_RETRIES, metavar="N",
        help="число повторов при сетевых ошибках и ответах 5xx",
    )
    group_checko.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT, metavar="СТРОКА",
        help="заголовок User-Agent",
    )
    group_checko.add_argument(
        "--proxy",
        default=None, metavar="URL",
        help="прокси вида http://user:pass@host:port (по умолчанию берётся из HTTPS_PROXY)",
    )
    group_checko.add_argument(
        "--no-query-by-name",
        action="store_true",
        help="не искать компанию по названию, если в реестре нет ИНН",
    )
    group_checko.add_argument(
        "--count-http-requests",
        action="store_true",
        help=(
            "списывать квоту за каждый HTTP-запрос, а не за компанию "
            "(по умолчанию поиск + карточка считаются одним запросом)"
        ),
    )
    group_checko.add_argument(
        "--retry-failed",
        action="store_true",
        help="повторить компании, по которым ранее были ошибки",
    )
    group_checko.add_argument(
        "--reset-state",
        action="store_true",
        help="ВНИМАНИЕ: удалить сохранённый прогресс и начать сбор с нуля",
    )
    group_checko.add_argument(
        "--max-companies",
        type=int, default=None, metavar="N",
        help="обработать не больше N компаний за запуск (для отладки)",
    )

    # ------------------------------- прочее --------------------------------- #
    group_misc = parser.add_argument_group("Прочее")
    group_misc.add_argument(
        "--with-diagnostics",
        action="store_true",
        help="добавить в отчёт служебные вкладки (нераспознанные строки, сводка)",
    )
    group_misc.add_argument(
        "--no-progress-bar",
        action="store_true",
        help="не показывать прогресс-бар (полезно при записи вывода в файл)",
    )
    group_misc.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="уровень подробности вывода в консоль",
    )
    group_misc.add_argument(
        "--version",
        action="version",
        version=f"nostroy-checko {__version__}",
    )
    return parser


def settings_from_args(args: argparse.Namespace) -> Settings:
    """Превращает разобранные аргументы в объект настроек."""
    report_date = date.today()
    if args.report_date:
        try:
            report_date = date.fromisoformat(args.report_date)
        except ValueError as exc:
            raise SystemExit(f"Некорректная дата отчёта {args.report_date!r}: {exc}") from exc

    return Settings(
        input_path=Path(args.input).expanduser(),
        output_dir=Path(args.output).expanduser(),
        dedupe_by=args.dedupe_by,
        header_scan_rows=max(1, args.header_scan_rows),
        header_max_span=max(1, args.header_max_span),
        content_sample=max(10, args.content_sample),
        use_checko=not args.no_checko,
        # Ключ можно не писать в командной строке — он подхватится из окружения.
        checko_api_key=args.checko_api_key or os.environ.get("CHECKO_API_KEY") or None,
        daily_limit=max(0, args.daily_limit),
        workers=max(1, args.workers),
        rps=max(0.0, args.rps),
        timeout=max(1.0, args.timeout),
        max_retries=max(0, args.max_retries),
        user_agent=args.user_agent,
        proxy=args.proxy,
        query_by_name=not args.no_query_by_name,
        count_http_requests=args.count_http_requests,
        retry_failed=args.retry_failed,
        reset_state=args.reset_state,
        max_companies=args.max_companies,
        log_level=args.log_level,
        with_diagnostics=args.with_diagnostics,
        report_date=report_date,
        no_progress_bar=args.no_progress_bar,
    )


def main(argv: list[str] | None = None) -> int:
    """Точка входа. Возвращает код завершения процесса."""
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = settings_from_args(args)
    settings.ensure_dirs()

    logger = setup_logging(settings.logs_dir, settings.log_level)
    logger.info("=" * 78)
    logger.info("Парсер реестра НОСТРОЙ + checko.ru, версия %s", __version__)
    logger.info("Вход:  %s", settings.input_path)
    logger.info("Выход: %s", settings.output_dir.resolve())
    logger.info("=" * 78)

    # Импорт здесь, а не наверху: так `--help` работает даже без установленных
    # тяжёлых зависимостей (pandas/openpyxl), и пользователь видит подсказку.
    try:
        from nostroy_checko.archives import ArchiveError
        from nostroy_checko.pipeline import run
    except ImportError as exc:
        logger.error("Не установлены зависимости: %s", exc)
        logger.error("Выполните: pip install -r requirements.txt")
        return 2

    try:
        result = run(settings)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except ArchiveError as exc:
        # Сообщение уже содержит инструкцию — трассировка тут только мешает.
        logger.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        logger.warning("Прервано пользователем")
        return 130
    except Exception as exc:  # noqa: BLE001 — показываем понятную ошибку, а не трассировку
        logger.exception("Критическая ошибка: %s", exc)
        return 1

    # ------------------------------ итоги ---------------------------------- #
    logger.info("=" * 78)
    for key, value in result.summary().items():
        logger.info("%-42s %s", key + ":", value)
    if result.report_path:
        logger.info("%-42s %s", "Итоговый отчёт:", result.report_path.resolve())
    logger.info("=" * 78)

    if result.checko_pending:
        logger.warning(
            "Осталось необработанных компаний: %d. Запустите ту же команду завтра "
            "после 00:00 — скрипт продолжит с места остановки.",
            result.checko_pending,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
