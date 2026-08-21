"""Чтение списка компаний из Excel — без требований к формату файла."""

from __future__ import annotations

import re
from pathlib import Path

import openpyxl

from .textutils import is_valid_inn


def read_companies(path: Path) -> list[tuple[str, str]]:
    """Пары «название, ИНН» с первого листа книги.

    Формат файла заранее не известен, поэтому колонки определяются по
    содержимому, а не по заголовкам: ИНН — то значение, что проходит
    проверку контрольной суммы. Так работает файл с шапкой и без неё,
    с колонками в любом порядке.

    Повторяющиеся ИНН отбрасываются: запрашивать одну компанию дважды
    незачем.
    """
    sheet = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    companies: list[tuple[str, str]] = []
    seen: set[str] = set()

    for row in sheet.iter_rows(values_only=True):
        values = [str(value).strip() for value in row if value not in (None, "")]
        if not values:
            continue

        inn = ""
        for value in values:
            digits = re.sub(r"\D", "", value)
            if len(digits) in (10, 12) and is_valid_inn(digits):
                inn = digits
                break
        if not inn:
            continue  # строка шапки или посторонние данные

        name = next(
            (value for value in values if re.sub(r"\D", "", value) != inn and len(value) > 3),
            "",
        )
        if inn not in seen:
            seen.add(inn)
            companies.append((name, inn))

    return companies
