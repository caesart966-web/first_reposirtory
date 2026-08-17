# -*- coding: utf-8 -*-
"""Логирование технических ошибок.

Главное правило: лог помогает найти причину сбоя, но не превращается
во вторую базу персональных данных.

В лог НЕ попадают: ФИО, паспортные данные, банковские счета, адреса,
телефоны, адреса электронной почты. Вместо значения пишется имя поля
и признак «заполнено / пусто».

ИНН и ОГРН пишутся полностью: это открытые сведения о юридическом лице,
и без них невозможно понять, к какому запуску относится запись.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "sro"

#: Поля, значения которых никогда не пишутся в лог.
SENSITIVE_FIELDS = {
    "director_full_name", "legal_address", "actual_address", "postal_address",
    "phone", "email", "website", "bank_name", "bank_account",
    "bank_corr_account", "bank_bik",
}


def setup(log_dir: Path, verbose: bool = False) -> logging.Logger:
    """Настроить логирование в файл logs/app.log (с ротацией)."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    if logger.handlers:
        return logger

    file_handler = RotatingFileHandler(
        log_dir / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-7s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(file_handler)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console)

    return logger


def get() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def safe_company(company) -> str:
    """Краткое и безопасное описание компании для лога."""
    filled = []
    empty = []
    for name in sorted(SENSITIVE_FIELDS):
        (filled if company.get(name) else empty).append(name)
    return (f"компания ИНН={company.inn or '—'} ОГРН={company.ogrn or '—'}; "
            f"заполнено: {', '.join(filled) or 'ничего'}; "
            f"пусто: {', '.join(empty) or 'ничего'}")


def safe_values(values: dict[str, str]) -> str:
    """Список переменных подстановки без самих значений."""
    parts = []
    for name in sorted(values):
        value = values[name]
        parts.append(f"{name}={'заполнено' if value else 'ПУСТО'}")
    return "; ".join(parts)
