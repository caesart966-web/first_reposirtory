"""
Сборка записей членов СРО из «сырых» листов.

Модуль отвечает за то, чтобы из каждой строки каждого листа каждого файла
получить :class:`~nostroy_checko.models.RegistryRecord` с полями:

* название компании / ИП / ФИО;
* ИНН;
* дата вступления в СРО;
* дата исключения (или ``None``);
* любые контактные данные, найденные в самом реестре.

Главный принцип — **ничего не пропускать**. Строка, из которой не удалось
извлечь ни ИНН, ни названия, не исчезает: она попадает в список
:class:`~nostroy_checko.models.UnrecognizedRow` и выгружается в
``output/parsed/unrecognized_rows.csv`` для ручной проверки.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from .column_mapper import (
    ROLE_ADDRESS,
    ROLE_CONTACT_OTHER,
    ROLE_DATE_EXIT,
    ROLE_DATE_JOIN,
    ROLE_DIRECTOR,
    ROLE_EMAIL,
    ROLE_INN,
    ROLE_NAME,
    ROLE_OGRN,
    ROLE_PHONE,
    ROLE_REG_NUMBER,
    ROLE_SRO,
    ROLE_STATUS,
    ROLE_WEBSITE,
    ColumnMap,
    build_column_map,
    guess_headers_for_headerless,
)
from .excel_reader import SheetData
from .logging_setup import get_logger
from .models import CompanyGroup, RegistryRecord, UnrecognizedRow
from .textutils import (
    cell_to_text,
    clean_text,
    extract_emails,
    extract_fio,
    extract_phones,
    extract_urls,
    find_inns_in_row,
    is_blank,
    merge_unique,
    normalize_header,
    normalize_inn,
    normalize_ogrn,
    parse_date,
)

logger = get_logger("registry")

#: Максимальная длина «превью» строки в отчёте о нераспознанных строках.
_PREVIEW_LIMIT = 500


# --------------------------------------------------------------------------- #
#                             Вспомогательные функции                          #
# --------------------------------------------------------------------------- #

def _row_is_empty(row: Sequence[Any]) -> bool:
    """Полностью пустая строка (в реестрах их много — это разделители блоков)."""
    return all(is_blank(value) for value in row)


def _row_repeats_header(row: Sequence[Any], column_map: ColumnMap) -> bool:
    """
    Повтор шапки внутри листа.

    В длинных выгрузках шапку часто дублируют на каждой «странице» —
    такие строки не являются данными.
    """
    if not column_map.normalized:
        return False
    normalized_row = [normalize_header(value) for value in row]
    matches = 0
    meaningful = 0
    for index, header in enumerate(column_map.normalized):
        if not header:
            continue
        meaningful += 1
        if index < len(normalized_row) and normalized_row[index] == header:
            matches += 1
    return meaningful >= 2 and matches >= max(2, int(meaningful * 0.6))


def _value_at(row: Sequence[Any], index: int | None) -> Any:
    """Безопасное получение значения ячейки по индексу колонки."""
    if index is None or index < 0 or index >= len(row):
        return None
    return row[index]


def _first_non_empty(row: Sequence[Any], indexes: Iterable[int]) -> str:
    """Первое непустое значение среди указанных колонок."""
    for index in indexes:
        text = clean_text(_value_at(row, index))
        if text:
            return text
    return ""


def _longest_non_empty(row: Sequence[Any], indexes: Iterable[int]) -> str:
    """
    Самое информативное (длинное) значение среди колонок.

    Нужно для названия: если в файле есть и «Полное наименование»,
    и «Сокращённое наименование», берём полное.
    """
    values = [clean_text(_value_at(row, index)) for index in indexes]
    values = [value for value in values if value]
    return max(values, key=len) if values else ""


#: Минимум заполненных строк, начиная с которого ищем «постоянные» колонки.
MIN_ROWS_FOR_CONSTANT_CHECK = 8


def detect_constant_columns(rows: Sequence[Sequence[Any]]) -> dict[int, str]:
    """
    Находит колонки, значение которых одинаково во ВСЕХ строках листа.

    Зачем. В выгрузках реестра НОСТРОЙ рядом с данными члена СРО идут реквизиты
    самой саморегулируемой организации — её наименование, телефон, адрес, почта.
    Они, естественно, одинаковы во всех строках файла. Если принять их за
    контакты компании, у всех членов окажется один и тот же телефон, и выгрузка
    станет бесполезной.

    Заголовок выдаёт такую колонку не всегда (она может называться просто
    «Телефон»), поэтому опираемся на сами данные: значение, не меняющееся на
    протяжении всего файла, физически не может быть контактом конкретного члена.

    Проверяются ВСЕ колонки, а не только опознанные как контактные: сплошной
    поиск телефонов и почты идёт по всей строке и иначе вытащил бы телефон СРО
    из соседней колонки в обход разбора по ролям.

    :return: ``{индекс колонки: постоянное значение}``.
    """
    if len(rows) < MIN_ROWS_FOR_CONSTANT_CHECK:
        return {}

    width = max((len(row) for row in rows), default=0)
    seen: dict[int, str] = {}          # колонка -> её единственное значение
    filled: dict[int, int] = {}        # сколько непустых значений встретилось
    varying: set[int] = set()          # колонки, где значения уже различались

    for row in rows:
        for index in range(width):
            if index in varying:
                continue               # ранний выход: колонка уже признана изменчивой
            text = clean_text(_value_at(row, index))
            if not text:
                continue
            filled[index] = filled.get(index, 0) + 1
            if index not in seen:
                seen[index] = text
            elif seen[index] != text:
                varying.add(index)
                seen.pop(index, None)

    return {
        index: value
        for index, value in seen.items()
        if filled.get(index, 0) >= MIN_ROWS_FOR_CONSTANT_CHECK
    }


# --------------------------------------------------------------------------- #
#                         Разбор одной строки таблицы                          #
# --------------------------------------------------------------------------- #

def parse_row(
    row: Sequence[Any],
    column_map: ColumnMap,
    sheet: SheetData,
    row_number: int,
    skip_columns: frozenset[int] = frozenset(),
) -> RegistryRecord | None:
    """
    Превращает строку таблицы в запись реестра.

    :param skip_columns: колонки, которые нельзя считать контактами компании
        (реквизиты самой СРО — см. :func:`detect_constant_contact_columns`).
        Их значения по-прежнему попадают в ``raw_fields``, то есть не теряются.

    Возвращает ``None``, если в строке нет ни названия, ни ИНН
    (вызывающий код зафиксирует её как нераспознанную).
    """
    record = RegistryRecord(
        source_file=sheet.display_path,
        source_sheet=sheet.sheet_name,
        source_row=row_number,
    )

    # ------------------------------ название ------------------------------- #
    # Из нескольких колонок с названием берём самое информативное: в выгрузках
    # рядом лежат полное и сокращённое наименование.
    record.name = _longest_non_empty(row, column_map.all_of(ROLE_NAME))

    # -------------------------------- ИНН ---------------------------------- #
    inn_columns = column_map.all_of(ROLE_INN)
    for index in inn_columns:
        candidate = normalize_inn(_value_at(row, index))
        if candidate:
            record.inn = candidate
            break
    if not record.inn:
        # Колонка с ИНН не опознана или пуста — ищем ИНН по всей строке.
        # Так запись не потеряется из-за нестандартной шапки.
        found = find_inns_in_row(row)
        if found:
            record.inn = found[0]
            record.warnings.append("ИНН найден автоматически по содержимому строки")

    # ------------------------------- ОГРН ---------------------------------- #
    record.ogrn = normalize_ogrn(_first_non_empty(row, column_map.all_of(ROLE_OGRN)))

    # -------------------------------- даты --------------------------------- #
    for index in column_map.all_of(ROLE_DATE_JOIN):
        parsed = parse_date(_value_at(row, index), sheet.date_mode)
        if parsed:
            record.date_join = parsed
            break
    for index in column_map.all_of(ROLE_DATE_EXIT):
        parsed = parse_date(_value_at(row, index), sheet.date_mode)
        if parsed:
            record.date_exit = parsed
            break
    if not column_map.all_of(ROLE_DATE_JOIN):
        record.warnings.append("на листе не найдена колонка с датой вступления")

    # --------------------------- прочие атрибуты --------------------------- #
    record.status = _first_non_empty(row, column_map.all_of(ROLE_STATUS))
    record.reg_number = _first_non_empty(row, column_map.all_of(ROLE_REG_NUMBER))
    record.sro_name = _first_non_empty(row, column_map.all_of(ROLE_SRO))

    # ------------------- контактные данные из реестра ---------------------- #
    for index in column_map.all_of(ROLE_PHONE):
        if index in skip_columns:
            continue
        text = clean_text(_value_at(row, index))
        if not text:
            continue
        phones = extract_phones(text)
        if phones:
            merge_unique(record.phones, phones)
        else:
            # Не удалось нормализовать — сохраняем как есть, данные не теряем.
            record.other_contacts[column_map.header_of(index)] = text

    for index in column_map.all_of(ROLE_EMAIL):
        if index in skip_columns:
            continue
        text = clean_text(_value_at(row, index))
        if not text:
            continue
        emails = extract_emails(text)
        if emails:
            merge_unique(record.emails, emails)
        else:
            record.other_contacts[column_map.header_of(index)] = text

    for index in column_map.all_of(ROLE_ADDRESS):
        if index in skip_columns:
            continue
        text = clean_text(_value_at(row, index))
        if text:
            merge_unique(record.addresses, [text])

    for index in column_map.all_of(ROLE_DIRECTOR):
        if index in skip_columns:
            continue
        text = clean_text(_value_at(row, index))
        if text:
            merge_unique(record.directors, [text])

    for index in column_map.all_of(ROLE_WEBSITE):
        if index in skip_columns:
            continue
        text = clean_text(_value_at(row, index))
        if not text:
            continue
        urls = extract_urls(text)
        merge_unique(record.websites, urls or [text])

    for index in column_map.all_of(ROLE_CONTACT_OTHER):
        if index in skip_columns:
            continue
        text = clean_text(_value_at(row, index))
        if text:
            record.other_contacts[column_map.header_of(index)] = text

    # --- сплошной поиск контактов по всей строке --------------------------- #
    # Телефоны и почта нередко «спрятаны» в колонках вроде «Примечание»,
    # склеены с адресом или лежат в колонке, роль которой определить не удалось.
    # Поэтому проходим по ВСЕМ ячейкам строки без исключений: повторы всё равно
    # отсекаются merge_unique, а вот пропустить контакт мы не имеем права.
    for index, value in enumerate(row):
        if index in skip_columns:
            continue
        text = clean_text(value)
        if not text:
            continue
        merge_unique(record.emails, extract_emails(text))
        merge_unique(record.phones, extract_phones(text))

    # ------------------------- «сырые» поля строки ------------------------- #
    for index, value in enumerate(row):
        text = clean_text(value)
        if not text:
            continue
        header = column_map.header_of(index)
        if header in record.raw_fields:
            header = f"{header} ({index + 1})"
        record.raw_fields[header] = text

    # ------------------------- название-«запасной» ------------------------- #
    if not record.name:
        # Названия нет в опознанной колонке — берём самое «похожее на название»
        # значение строки (длинный текст с буквами), чтобы не потерять запись.
        best = ""
        for index, value in enumerate(row):
            if index in inn_columns:
                continue
            text = clean_text(value)
            if len(text) > len(best) and any(char.isalpha() for char in text):
                best = text
        if best and (record.inn or len(best) >= 5):
            record.name = best
            record.warnings.append("название взято эвристически (колонка не опознана)")

    if not record.has_identity:
        return None
    # Название без единой буквы и без ИНН — это не член СРО, а строка «Итого»,
    # номер страницы или иной технический мусор. В отчёт такая строка попадёт
    # как нераспознанная (с полным содержимым), но записью реестра не станет.
    if not record.inn and not any(char.isalpha() for char in record.name):
        return None

    # Руководитель мог не иметь отдельной колонки, но быть в названии/примечании.
    if not record.directors and record.name and not record.inn:
        fio = extract_fio(record.name)
        if fio and fio == record.name:
            record.directors.append(fio)

    return record


# --------------------------------------------------------------------------- #
#                              Разбор листа целиком                            #
# --------------------------------------------------------------------------- #

def describe_columns(
    sheet: SheetData,
    column_map: ColumnMap,
    max_samples: int = 3,
) -> list[dict[str, Any]]:
    """
    Описывает, как распознан каждый столбец листа: заголовок, назначенная роль
    и примеры значений.

    Нужна, когда в отчёте пусто там, где в исходном файле данные есть.
    По этой выжимке сразу видно, чем именно столбец был признан — и почему
    нужная колонка не попала в отчёт. Файл маленький, его удобно переслать,
    в отличие от всей выгрузки.
    """
    role_by_column: dict[int, list[str]] = {}
    for role, indexes in column_map.roles.items():
        for index in indexes:
            role_by_column.setdefault(index, []).append(role)

    start = column_map.data_start_row
    width = max((len(row) for row in sheet.rows), default=0)
    described: list[dict[str, Any]] = []
    for index in range(width):
        samples: list[str] = []
        for row in sheet.rows[start:]:
            text = clean_text(_value_at(row, index))
            if text:
                samples.append(text[:60])
            if len(samples) >= max_samples:
                break
        described.append(
            {
                "Файл": sheet.display_path,
                "Лист": sheet.sheet_name,
                "Колонка": index + 1,
                "Заголовок": column_map.header_of(index),
                "Распознано как": ", ".join(sorted(role_by_column.get(index, []))) or "—",
                "Примеры значений": " | ".join(samples),
            }
        )
    return described


def parse_sheet(
    sheet: SheetData,
    scan_rows: int = 60,
    max_span: int = 3,
    sample_size: int = 400,
    column_report: list[dict[str, Any]] | None = None,
) -> tuple[list[RegistryRecord], list[UnrecognizedRow], ColumnMap]:
    """
    Разбирает один лист: определяет структуру и проходит ВСЕ строки.

    :return: ``(записи, нераспознанные строки, карта колонок)``.
    """
    if column_report is None:
        column_report = []
    if not sheet.rows:
        return [], [], ColumnMap()

    column_map = build_column_map(
        sheet.rows,
        scan_rows=scan_rows,
        max_span=max_span,
        sample_size=sample_size,
        date_mode=sheet.date_mode,
    )
    if not column_map.headers:
        column_map.headers = guess_headers_for_headerless(sheet.rows)
        column_map.normalized = ["" for _ in column_map.headers]

    start = column_map.data_start_row

    # Отсекаем реквизиты самой СРО: контактные колонки с одинаковым значением
    # во всех строках — это телефон/адрес/почта саморегулируемой организации,
    # а не члена. Иначе у всех компаний окажется один и тот же телефон.
    constant_columns = detect_constant_columns(sheet.rows[start:])
    skip_columns = frozenset(constant_columns)
    for index, value in sorted(constant_columns.items()):
        logger.info(
            "  лист %r: колонка %r одинакова во всех строках (%r) — "
            "это реквизит самой СРО, в контакты компаний не пойдёт",
            sheet.sheet_name, column_map.header_of(index), value[:60],
        )

    records: list[RegistryRecord] = []
    unrecognized: list[UnrecognizedRow] = []
    for offset, row in enumerate(sheet.rows[start:]):
        row_number = start + offset + 1          # нумерация как в Excel, с 1
        if _row_is_empty(row):
            continue
        if _row_repeats_header(row, column_map):
            continue

        try:
            record = parse_row(row, column_map, sheet, row_number, skip_columns)
        except Exception as exc:  # noqa: BLE001 — одна битая строка не рушит разбор
            logger.error("Ошибка разбора строки %s листа %r: %s", row_number, sheet.sheet_name, exc)
            unrecognized.append(
                UnrecognizedRow(
                    file_path=sheet.display_path,
                    sheet_name=sheet.sheet_name,
                    row_number=row_number,
                    reason=f"ошибка разбора: {type(exc).__name__}: {exc}",
                    preview=_row_preview(row),
                )
            )
            continue

        if record is None:
            unrecognized.append(
                UnrecognizedRow(
                    file_path=sheet.display_path,
                    sheet_name=sheet.sheet_name,
                    row_number=row_number,
                    reason="не найдены ни ИНН, ни наименование",
                    preview=_row_preview(row),
                )
            )
            continue

        records.append(record)

    column_report.extend(describe_columns(sheet, column_map))
    logger.info(
        "  лист %r: строк %d, записей %d, нераспознано %d (%s)",
        sheet.sheet_name,
        sheet.row_count,
        len(records),
        len(unrecognized),
        column_map.describe(),
    )
    return records, unrecognized, column_map


def _row_preview(row: Sequence[Any]) -> str:
    """Короткое текстовое представление строки для диагностики."""
    parts = [cell_to_text(value) for value in row]
    preview = " | ".join(part for part in parts if part)
    return preview[:_PREVIEW_LIMIT]


# --------------------------------------------------------------------------- #
#                           Разбор всех листов сразу                           #
# --------------------------------------------------------------------------- #

def parse_sheets(
    sheets: Iterable[SheetData],
    scan_rows: int = 60,
    max_span: int = 3,
    sample_size: int = 400,
) -> tuple[list[RegistryRecord], list[UnrecognizedRow]]:
    """Прогоняет :func:`parse_sheet` по всем листам и собирает общий результат."""
    all_records: list[RegistryRecord] = []
    all_unrecognized: list[UnrecognizedRow] = []
    for sheet in sheets:
        try:
            records, unrecognized, _ = parse_sheet(sheet, scan_rows, max_span, sample_size)
        except Exception as exc:  # noqa: BLE001 — битый лист не должен ронять запуск
            logger.error("Лист %r файла %s пропущен из-за ошибки: %s",
                         sheet.sheet_name, sheet.display_path, exc)
            continue
        all_records.extend(records)
        all_unrecognized.extend(unrecognized)
    return all_records, all_unrecognized


# --------------------------------------------------------------------------- #
#                           Группировка (дедупликация)                         #
# --------------------------------------------------------------------------- #

def group_records(records: Sequence[RegistryRecord], mode: str = "inn") -> list[CompanyGroup]:
    """
    Объединяет записи об одной и той же компании.

    Одна компания встречается в реестрах многократно (разные файлы, листы,
    выгрузки). Запрос к checko.ru стоит единицы суточной квоты, поэтому
    делать его повторно для того же ИНН бессмысленно.

    :param mode: ``inn`` — группировка по ИНН (по умолчанию, экономит квоту);
                 ``name_inn`` — буквально по паре «Название + ИНН».
    """
    groups: dict[str, CompanyGroup] = {}
    order: list[str] = []
    for record in records:
        key = record.dedupe_key(mode)
        if key not in groups:
            groups[key] = CompanyGroup(key=key)
            order.append(key)
        groups[key].records.append(record)

    result = [groups[key] for key in order]
    logger.info(
        "Сгруппировано: %d записей -> %d уникальных компаний (режим дедупликации: %s)",
        len(records),
        len(result),
        mode,
    )
    return result
