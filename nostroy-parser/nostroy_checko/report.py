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
from .textutils import format_date, join_unique, truncate

logger = get_logger("report")

#: Максимальная ширина колонки в символах (иначе отчёт нечитаем).
_MAX_COLUMN_WIDTH = 60
_MIN_COLUMN_WIDTH = 10

#: Формат отображения дат в отчёте.
_DATE_FORMAT = "DD.MM.YYYY"

#: Названия обязательных вкладок (строго по ТЗ).
SHEET_CHECKO = "checko_contacts"
SHEET_NOSTROY = "nostroy_contacts"
SHEET_COMBINED = "combined"
SHEET_UNRECOGNIZED = "unrecognized_rows"
SHEET_SUMMARY = "run_summary"


# --------------------------------------------------------------------------- #
#                        Подготовка строк для вкладок                          #
# --------------------------------------------------------------------------- #

def build_checko_rows(groups: Sequence[CompanyGroup]) -> tuple[list[str], list[list[Any]]]:
    """Строки вкладки ``checko_contacts`` — только данные с checko.ru."""
    headers = [
        "Название компании (реестр)",
        "Название компании (checko.ru)",
        "ИНН",
        "ОГРН (checko.ru)",
        "Телефоны (checko.ru)",
        "Email (checko.ru)",
        "Адрес (checko.ru)",
        "Руководитель (checko.ru)",
        "Сайт (checko.ru)",
        "Статус запроса",
        "ИНН совпал",
        "Ссылка на карточку",
        "Дата получения",
        "Ошибка",
    ]
    rows: list[list[Any]] = []
    for group in groups:
        checko = group.checko
        rows.append(
            [
                group.name,
                checko.name if checko else "",
                group.inn,
                checko.ogrn if checko else "",
                join_unique(checko.phones) if checko else "",
                join_unique(checko.emails) if checko else "",
                join_unique(checko.addresses) if checko else "",
                join_unique(checko.directors) if checko else "",
                join_unique(checko.websites) if checko else "",
                checko.status if checko else "не запрашивалось",
                _bool_to_text(checko.inn_matched) if checko else "",
                checko.url if checko else "",
                checko.fetched_at if checko else "",
                checko.error if checko else "",
            ]
        )
    return headers, rows


def build_nostroy_rows(records: Sequence[RegistryRecord]) -> tuple[list[str], list[list[Any]]]:
    """
    Строки вкладки ``nostroy_contacts`` — контакты из реестра НОСТРОЙ.

    Одна строка отчёта = одна исходная запись реестра (со ссылкой на файл,
    лист и номер строки), поэтому ни одна запись не «схлопывается» и не теряется.
    """
    headers = [
        "Название компании / ИП",
        "ИНН",
        "ОГРН",
        "Дата вступления в СРО",
        "Дата исключения",
        "Статус членства",
        "Телефон (реестр)",
        "Email (реестр)",
        "Адрес (реестр)",
        "Руководитель (реестр)",
        "Сайт (реестр)",
        "Прочие контакты (реестр)",
        "Регистрационный номер",
        "СРО",
        "Файл-источник",
        "Лист",
        "Строка",
        "Примечания разбора",
    ]
    rows: list[list[Any]] = []
    for record in records:
        rows.append(
            [
                record.name,
                record.inn,
                record.ogrn,
                record.date_join,
                record.date_exit,
                record.status,
                join_unique(record.phones),
                join_unique(record.emails),
                join_unique(record.addresses),
                join_unique(record.directors),
                join_unique(record.websites),
                join_unique(f"{key}: {value}" for key, value in record.other_contacts.items()),
                record.reg_number,
                record.sro_name,
                record.source_file,
                record.source_sheet,
                record.source_row,
                join_unique(record.warnings),
            ]
        )
    return headers, rows


def build_combined_rows(groups: Sequence[CompanyGroup]) -> tuple[list[str], list[list[Any]]]:
    """
    Строки вкладки ``combined``.

    Порядок колонок соответствует требуемому составу выгрузки:
    название, ИНН, контакты с checko.ru, даты вступления/исключения,
    контакты из реестра НОСТРОЙ — плюс объединённые списки телефонов и email.
    """
    headers = [
        "Название компании",
        "ИНН",
        # --- контактные данные с checko.ru --- #
        "Телефон (checko.ru)",
        "Email (checko.ru)",
        "Адрес (checko.ru)",
        "Руководитель (checko.ru)",
        "Контакты checko.ru (одной строкой)",
        # --- даты членства --- #
        "Дата вступления",
        "Дата исключения",
        # --- контактные данные из реестра НОСТРОЙ --- #
        "Телефон (реестр НОСТРОЙ)",
        "Email (реестр НОСТРОЙ)",
        "Адрес (реестр НОСТРОЙ)",
        "Руководитель (реестр НОСТРОЙ)",
        "Контакты реестра (одной строкой)",
        # --- объединённые данные --- #
        "Все телефоны",
        "Все email",
        "Все адреса",
        "Все руководители",
        "Сайт",
        # --- служебное --- #
        "ОГРН",
        "Статус членства",
        "Статус запроса checko.ru",
        "Ссылка на checko.ru",
        "Варианты написания названия",
        "Записей в реестре",
        "Источники (файл | лист | строка)",
    ]
    rows: list[list[Any]] = []
    for group in groups:
        checko = group.checko
        rows.append(
            [
                group.name,
                group.inn,
                join_unique(checko.phones) if checko else "",
                join_unique(checko.emails) if checko else "",
                join_unique(checko.addresses) if checko else "",
                join_unique(checko.directors) if checko else "",
                checko.contacts_summary() if checko else "",
                group.date_join,
                group.date_exit,
                join_unique(group.registry_phones),
                join_unique(group.registry_emails),
                join_unique(group.registry_addresses),
                join_unique(group.registry_directors),
                group.registry_contacts_summary(),
                join_unique(group.all_phones),
                join_unique(group.all_emails),
                join_unique(group.all_addresses),
                join_unique(group.all_directors),
                join_unique(group.registry_websites + (checko.websites if checko else [])),
                group.ogrn or (checko.ogrn if checko else ""),
                group.status,
                group.checko_status,
                checko.url if checko else "",
                join_unique(group.all_names),
                len(group.records),
                truncate(join_unique(group.sources), 1000),
            ]
        )
    return headers, rows


def build_unrecognized_rows(items: Sequence[UnrecognizedRow]) -> tuple[list[str], list[list[Any]]]:
    """Строки служебной вкладки с нераспознанными строками исходных файлов."""
    headers = ["Файл", "Лист", "Строка", "Причина", "Содержимое строки"]
    rows = [
        [item.file_path, item.sheet_name, item.row_number, item.reason, truncate(item.preview, 2000)]
        for item in items
    ]
    return headers, rows


def build_summary_rows(summary: dict[str, Any]) -> tuple[list[str], list[list[Any]]]:
    """Строки служебной вкладки со сводкой по запуску."""
    headers = ["Показатель", "Значение"]
    rows = [[key, value] for key, value in summary.items()]
    return headers, rows


def _bool_to_text(value: bool | None) -> str:
    """``True/False/None`` -> ``да/нет/—`` для отображения в отчёте."""
    if value is None:
        return "—"
    return "да" if value else "нет"


# --------------------------------------------------------------------------- #
#                              Запись Excel-файла                              #
# --------------------------------------------------------------------------- #

def _write_sheet(workbook: Any, title: str, headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    """
    Записывает одну вкладку: шапка, данные, автофильтр, закрепление, ширины.

    ИНН пишется текстом — иначе Excel съедает ведущие нули и показывает
    ``7,70708E+09`` вместо номера.
    """
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    worksheet = workbook.create_sheet(title=title[:31])
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_alignment = Alignment(vertical="center", wrap_text=True)

    worksheet.append(list(headers))
    for cell in worksheet[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    # Колонки, которые обязаны быть текстовыми (ИНН, ОГРН, телефоны).
    text_columns = {
        index
        for index, header in enumerate(headers, start=1)
        if any(marker in header.upper() for marker in ("ИНН", "ОГРН", "ТЕЛЕФОН"))
    }
    date_columns = {
        index
        for index, header in enumerate(headers, start=1)
        if "ДАТА" in header.upper() and "ПОЛУЧЕНИЯ" not in header.upper()
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
        worksheet.auto_filter.ref = (
            f"A1:{get_column_letter(len(headers))}{len(rows) + 1}"
        )


def write_report(
    path: Path,
    groups: Sequence[CompanyGroup],
    records: Sequence[RegistryRecord],
    unrecognized: Sequence[UnrecognizedRow] = (),
    summary: dict[str, Any] | None = None,
    with_diagnostics: bool = False,
) -> Path:
    """
    Формирует итоговый Excel-файл со всеми вкладками.

    :param path:             куда сохранить (``final_report_YYYY-MM-DD.xlsx``);
    :param groups:           уникальные компании с данными checko.ru;
    :param records:          все записи реестра (для вкладки nostroy_contacts);
    :param unrecognized:     нераспознанные строки (служебная вкладка);
    :param summary:          сводка по запуску (служебная вкладка);
    :param with_diagnostics: добавлять ли служебные вкладки;
    :return: путь к сохранённому файлу.
    """
    from openpyxl import Workbook

    workbook = Workbook()
    # Workbook создаётся с пустым листом — удаляем его, вкладки добавляем сами.
    workbook.remove(workbook.active)

    checko_headers, checko_rows = build_checko_rows(groups)
    _write_sheet(workbook, SHEET_CHECKO, checko_headers, checko_rows)

    nostroy_headers, nostroy_rows = build_nostroy_rows(records)
    _write_sheet(workbook, SHEET_NOSTROY, nostroy_headers, nostroy_rows)

    combined_headers, combined_rows = build_combined_rows(groups)
    _write_sheet(workbook, SHEET_COMBINED, combined_headers, combined_rows)

    if with_diagnostics:
        headers, rows = build_unrecognized_rows(unrecognized)
        _write_sheet(workbook, SHEET_UNRECOGNIZED, headers, rows)
        headers, rows = build_summary_rows(summary or {})
        _write_sheet(workbook, SHEET_SUMMARY, headers, rows)

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(str(path))
    workbook.close()
    logger.info(
        "Отчёт сохранён: %s (компаний %d, записей реестра %d)",
        path, len(groups), len(records),
    )
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
