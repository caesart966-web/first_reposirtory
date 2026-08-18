"""
Настройка логирования.

Логи одновременно пишутся в консоль (для оператора) и в файл
``output/logs/run_YYYY-MM-DD.log`` (для разбора инцидентов постфактум).
"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

LOGGER_NAME = "nostroy_checko"

_CONSOLE_FMT = "%(asctime)s | %(levelname)-7s | %(message)s"
_FILE_FMT = "%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s"
_DATE_FMT = "%H:%M:%S"


def setup_logging(logs_dir: Path, level: str = "INFO") -> logging.Logger:
    """
    Инициализирует корневой логгер пакета.

    :param logs_dir: папка для файлов логов (создаётся при необходимости);
    :param level:    уровень логирования консоли (DEBUG/INFO/WARNING/ERROR);
    :return:         настроенный логгер.
    """
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)          # в файл пишем всё, в консоль — по уровню
    logger.propagate = False

    # Повторная инициализация (например, в тестах) не должна плодить обработчики.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(getattr(logging, level.upper(), logging.INFO))
    console.setFormatter(logging.Formatter(_CONSOLE_FMT, datefmt=_DATE_FMT))
    logger.addHandler(console)

    log_file = logs_dir / f"run_{date.today().isoformat()}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FILE_FMT))
    logger.addHandler(file_handler)

    # Библиотеки не должны засорять вывод.
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    logger.debug("Логирование инициализировано, файл: %s", log_file)
    return logger


def get_logger(suffix: str | None = None) -> logging.Logger:
    """Возвращает дочерний логгер пакета (например, ``nostroy_checko.checko``)."""
    return logging.getLogger(LOGGER_NAME if not suffix else f"{LOGGER_NAME}.{suffix}")
