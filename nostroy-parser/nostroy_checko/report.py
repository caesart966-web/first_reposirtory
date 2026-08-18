"""
Формирование итогового Excel-отчёта и промежуточных выгрузок.

Итоговый файл ``output/final_report_YYYY-MM-DD.xlsx`` содержит три обязательные
вкладки:

1. ``checko_contacts``  — только контакты, полученные с checko.ru;
2. ``nostroy_contacts`` — только контакты из самого реестра НОСТРОЙ
   (по одной строке на каждую исходную запись — ничего не теряется);
3. ``combined``         — сводная таблица: название, ИНН, все телефоны,
   все email, адреса, руководители, даты вступления и исключения.

По ключу ``--with-diagnostics`` добавляются служебные вкладки
``unrecognized_rows`` и ``run_summary``.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from .logging_setup import get_logger
from .models import CompanyGroup, RegistryRecord, UnrecognizedRow
from .textutils import director_fio, format_date, join_unique, truncate

logger = get_logger("report")

#: Максимальная ширина колонки в символах (иначе отчёт нечитаем).
_MAX_COLUMN_WIDTH = 60
_MIN_COLUMN_WIDTH = 10

#: Формат отображения дат в отчёте.
_DATE_FORMAT = "DD.MM.YYYY"

#: Единственный лист отчёта.
SHEET_NAME = "Контакты"


# --------------------------------------------------------------------------- #
#                          Подготовка строк отчёта                             #
# --------------------------------------------------------------------------- #

def build_report_rows(groups: Sequence[CompanyGroup]) -> tuple[list[str], list[list[Any]]]:
    """
    Формирует единственную таблицу отчёта — по строке на компанию.

    Контакты берутся с checko.ru, а если сервис по компании ничего не дал —
    из самого реестра НОСТРОЙ (там обычно есть адрес и руководитель, иногда
    телефон и почта). Даты членства — из реестра НОСТРОЙ. Даты
    проставляются сразу всем компаниям, ещё до обращения к checko.ru: они уже
    есть в реестре и не зависят от суточной квоты. Телефоны, наоборот,
    наполняются по мере обработки — день за днём.

    «Статус членства» — короткое «действует» / «исключён» для сортировки.
    В колонке «Руководитель» выводится только ФИО, без должности.
    """
    headers = [
        "Название компании",
        "ИНН",
        "Телефон",
        "Email",
        "Адрес",
        "Руководитель",
        "Дата вступления в СРО",
        "Дата исключения из СРО",
        "Статус членства",
        "Статус запроса",
    ]
    rows: list[list[Any]] = []
    for group in groups:
        checko = group.checko
        rows.append(
            [
                group.name,
                group.inn,
                join_unique(group.best_phones),
                join_unique(group.best_emails),
                join_unique(group.best_addresses),
                join_unique(director_fio(value) for value in group.best_directors),
                group.date_join,
                group.date_exit,
                group.membership_status,
                checko.status if checko else "не запрашивалось",
            ]
        )
    return headers, rows


# --------------------------------------------------------------------------- #
#                              Запись Excel-файла                              #
# --------------------------------------------------------------------------- #

def _write_sheet(
    workbook: Any,
    title: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
) -> None:
    """
    Записывает лист: шапка, данные, автофильтр, закрепление строки, ширины.

    Оформление намеренно скупое: жирная шапка и ничего больше. Заливку и цвета
    не используем — таблицу читают и фильтруют, а не разглядывают.

    ИНН и телефоны пишутся текстом: иначе Excel съедает ведущие нули и
    показывает ``7,70708E+09`` вместо номера. Даты пишутся настоящими датами,
    поэтому по ним работают сортировка и фильтр по периоду.
    """
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    worksheet = workbook.create_sheet(title=title[:31])

    worksheet.append(list(headers))
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(vertical="center")

    text_columns = {
        index
        for index, header in enumerate(headers, start=1)
        if any(marker in header.upper() for marker in ("ИНН", "ОГРН", "ТЕЛЕФОН"))
    }
    date_columns = {
        index for index, header in enumerate(headers, start=1) if "ДАТА" in header.upper()
    }

    widths = [len(str(header)) for header in headers]
    for row in rows:
        prepared: list[Any] = []
        for index, value in enumerate(row, start=1):
            if isinstance(value, date):
                prepared.append(value)
            elif value is None:
                prepared.append("")
            elif isinstance(value, (int, float)) and index not in text_columns:
                prepared.append(value)
            else:
                prepared.append(truncate(str(value)))
        worksheet.append(prepared)
        row_index = worksheet.max_row
        for index, value in enumerate(prepared, start=1):
            cell = worksheet.cell(row=row_index, column=index)
            if index in date_columns and isinstance(value, date):
                cell.number_format = _DATE_FORMAT
            elif index in text_columns:
                cell.number_format = "@"
            length = len(format_date(value) if isinstance(value, date) else str(value))
            if index - 1 < len(widths):
                widths[index - 1] = max(widths[index - 1], min(length, _MAX_COLUMN_WIDTH))

    for index, width in enumerate(widths, start=1):
        worksheet.column_dimensions[get_column_letter(index)].width = max(
            _MIN_COLUMN_WIDTH, min(width + 2, _MAX_COLUMN_WIDTH)
        )

    worksheet.freeze_panes = "A2"
    if rows:
        worksheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(rows) + 1}"


def write_report(path: Path, groups: Sequence[CompanyGroup]) -> Path:
    """
    Формирует итоговый Excel-файл — один лист «Контакты», по строке на компанию.

    Всё, что в таблицу не вошло, сохраняется рядом в ``output/parsed/``:
    построчные данные реестра — в ``records.json``, нераспознанные строки —
    в ``unrecognized_rows.csv``.
    """
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.remove(workbook.active)          # убираем пустой лист по умолчанию

    headers, rows = build_report_rows(groups)
    _write_sheet(workbook, SHEET_NAME, headers, rows)

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(str(path))
    workbook.close()
    logger.info("Отчёт сохранён: %s (компаний %d)", path, len(groups))
    return path


# --------------------------------------------------------------------------- #
#                          Промежуточные выгрузки                              #
# --------------------------------------------------------------------------- #

def write_parsed_artifacts(
    parsed_dir: Path,
    records: Sequence[RegistryRecord],
    groups: Sequence[CompanyGroup],
    unrecognized: Sequence[UnrecognizedRow],
    files_index: Sequence[dict[str, Any]],
) -> None:
    """
    Сохраняет промежуточные результаты разбора в ``output/parsed/``.

    Эти файлы нужны и для отладки, и как «страховка»: если формирование
    итогового Excel по какой-то причине не завершится, данные уже на диске.
    """
    parsed_dir.mkdir(parents=True, exist_ok=True)

    _write_json(parsed_dir / "records.json", [record.to_dict() for record in records])
    _write_json(parsed_dir / "companies.json", [group.to_dict() for group in groups])
    _write_csv(
        parsed_dir / "unrecognized_rows.csv",
        ["Файл", "Лист", "Строка", "Причина", "Содержимое строки"],
        [
            [item.file_path, item.sheet_name, item.row_number, item.reason, item.preview]
            for item in unrecognized
        ],
    )
    _write_csv(
        parsed_dir / "files_index.csv",
        ["Файл", "Листов", "Строк", "Записей", "Нераспознано"],
        [
            [
                item.get("file", ""),
                item.get("sheets", 0),
                item.get("rows", 0),
                item.get("records", 0),
                item.get("unrecognized", 0),
            ]
            for item in files_index
        ],
    )
    logger.info("Промежуточные выгрузки сохранены в %s", parsed_dir)


def _write_json(path: Path, payload: Any) -> None:
    """Сохраняет JSON в UTF-8 с читаемым форматированием."""
    try:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except OSError as exc:
        logger.error("Не удалось записать %s: %s", path, exc)


def _write_csv(path: Path, headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    """Сохраняет CSV с BOM (чтобы Excel сразу открывал его в правильной кодировке)."""
    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle, delimiter=";")
            writer.writerow(headers)
            writer.writerows(rows)
    except OSError as exc:
        logger.error("Не удалось записать %s: %s", path, exc)
