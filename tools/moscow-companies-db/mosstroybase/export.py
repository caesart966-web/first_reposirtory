"""Экспорт базы в CSV (для Excel: utf-8-sig, разделитель «;») и XLSX."""

from __future__ import annotations

import csv
from pathlib import Path

from .db import CompanyDB

COLUMNS = (
    ("inn", "ИНН"),
    ("ogrn", "ОГРН"),
    ("name", "Наименование"),
    ("name_short", "Краткое наименование"),
    ("okved_main", "ОКВЭД основной"),
    ("okved_add", "ОКВЭД дополнительные"),
    ("address", "Адрес"),
    ("egrul_status", "Статус"),
    ("msp_category", "Категория МСП"),
    ("phones", "Телефоны"),
    ("emails", "E-mail"),
    ("website", "Сайт"),
    ("sro_info", "СРО"),
    ("sources", "Источники"),
)


def _rows(
    db: CompanyDB, only_active: bool, with_contacts_only: bool,
    inns: set[str] | None = None, include_sro: bool = False,
):
    for company in db.iter_all():
        if inns is not None and company["inn"] not in inns:
            continue
        if not include_sro and company.get("sro_member") == 1:
            continue
        if only_active and company.get("is_active") == 0:
            continue
        if with_contacts_only and not company["emails"] and not company["phones"]:
            continue
        row = []
        for field, _title in COLUMNS:
            value = company.get(field)
            if isinstance(value, list):
                value = "; ".join(value)
            row.append(value if value is not None else "")
        yield row


def export_csv(
    db: CompanyDB, path: str | Path, only_active: bool, with_contacts_only: bool,
    inns: set[str] | None = None, include_sro: bool = False,
) -> int:
    count = 0
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow([title for _field, title in COLUMNS])
        for row in _rows(db, only_active, with_contacts_only, inns, include_sro):
            writer.writerow(row)
            count += 1
    return count


def export_xlsx(
    db: CompanyDB, path: str | Path, only_active: bool, with_contacts_only: bool,
    inns: set[str] | None = None, include_sro: bool = False,
) -> int:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("Для экспорта в XLSX установите openpyxl: pip install openpyxl") from exc

    wb = Workbook()
    ws = wb.active
    ws.title = "Компании"
    ws.append([title for _field, title in COLUMNS])
    count = 0
    for row in _rows(db, only_active, with_contacts_only, inns, include_sro):
        ws.append(row)
        count += 1
    ws.freeze_panes = "A2"
    wb.save(path)
    return count
