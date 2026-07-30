"""Экспорт базы в CSV (для Excel: utf-8-sig, разделитель «;») и XLSX."""

from __future__ import annotations

import csv
from pathlib import Path

from .db import CompanyDB
from .normalize import is_valid_phone

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
    ("reg_date", "Дата регистрации"),
    ("employees", "Сотрудников (СЧР)"),
    ("taxes_paid", "Налоги уплачено, ₽"),
    ("bankruptcy", "Банкротство"),
    ("director", "Руководитель"),
    ("director_post", "Должность"),
    ("phones", "Телефоны (Checko)"),
    ("phones_site", "Телефоны с сайта (проверить)"),
    ("emails", "E-mail"),
    ("website", "Сайт"),
    ("sro_info", "СРО"),
    ("sources", "Источники"),
)


def _rows(
    db: CompanyDB, only_active: bool, with_contacts_only: bool,
    inns: set[str] | None = None, include_sro: bool = False,
    alive_only: bool = False,
):
    for company in db.iter_all():
        if inns is not None and company["inn"] not in inns:
            continue
        if not include_sro and company.get("sro_member") == 1:
            continue
        # Банкроты — не лиды: исключаются из выгрузок всегда
        if company.get("bankruptcy") == 1:
            continue
        if only_active and company.get("is_active") == 0:
            continue
        if alive_only and not (
            (company.get("employees") or 0) > 0 or (company.get("taxes_paid") or 0) > 0
        ):
            continue
        if (with_contacts_only and not company["emails"] and not company["phones"]
                and not company.get("phones_site")):
            continue
        row = []
        for field, _title in COLUMNS:
            value = company.get(field)
            if field == "bankruptcy":
                value = "банкротство" if value == 1 else ""
            if field in ("phones", "phones_site") and isinstance(value, list):
                # Перестраховка: старые записи могли содержать ложные
                # срабатывания регулярки — в выгрузку идут только валидные
                value = [p for p in value if is_valid_phone(p)]
            if isinstance(value, list):
                value = "; ".join(value)
            row.append(value if value is not None else "")
        yield row


def export_csv(
    db: CompanyDB, path: str | Path, only_active: bool, with_contacts_only: bool,
    inns: set[str] | None = None, include_sro: bool = False,
    alive_only: bool = False,
) -> int:
    count = 0
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow([title for _field, title in COLUMNS])
        for row in _rows(db, only_active, with_contacts_only, inns, include_sro,
                         alive_only):
            writer.writerow(row)
            count += 1
    return count


def export_xlsx(
    db: CompanyDB, path: str | Path, only_active: bool, with_contacts_only: bool,
    inns: set[str] | None = None, include_sro: bool = False,
    alive_only: bool = False,
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
    for row in _rows(db, only_active, with_contacts_only, inns, include_sro,
                     alive_only):
        ws.append(row)
        count += 1
    ws.freeze_panes = "A2"
    wb.save(path)
    return count
