"""
Определение строки заголовков и назначение «ролей» колонкам.

По ТЗ нельзя делать предположений о названиях столбцов, поэтому работа идёт
в два независимых этапа:

1. **По заголовкам.** Заголовок нормализуется (регистр, «ё», пунктуация,
   переносы строк) и сопоставляется с набором регулярных выражений. Шапка
   ищется в первых N строках листа и может занимать несколько строк
   («многоэтажные» шапки с объединёнными ячейками).
2. **По содержимому.** Всё, что не удалось определить по заголовку (или если
   шапки нет вовсе), определяется по самим данным: ИНН — по контрольной сумме,
   даты — по разбору, телефоны/email/адреса — по формату значений.

Итог — :class:`ColumnMap`, который сообщает, в какой колонке что лежит.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date as _date
from typing import Any, Sequence

from .logging_setup import get_logger
from .textutils import (
    cell_to_text,
    clean_text,
    extract_emails,
    extract_phones,
    has_org_marker,
    is_valid_inn,
    looks_like_address,
    looks_like_company_name,
    looks_like_fio,
    normalize_header,
    normalize_inn,
    parse_date,
)

logger = get_logger("columns")

# --------------------------------------------------------------------------- #
#                                    Роли                                      #
# --------------------------------------------------------------------------- #

ROLE_NAME = "name"                 # наименование компании / ИП / ФИО
ROLE_INN = "inn"                   # ИНН
ROLE_OGRN = "ogrn"                 # ОГРН / ОГРНИП
ROLE_DATE_JOIN = "date_join"       # дата вступления в СРО
ROLE_DATE_EXIT = "date_exit"       # дата исключения из СРО
ROLE_STATUS = "status"             # статус членства
ROLE_REG_NUMBER = "reg_number"     # регистрационный номер в реестре
ROLE_SRO = "sro"                   # наименование СРО
ROLE_PHONE = "phone"               # телефон / факс
ROLE_EMAIL = "email"               # электронная почта
ROLE_ADDRESS = "address"           # адрес
ROLE_DIRECTOR = "director"         # руководитель
ROLE_WEBSITE = "website"           # сайт
ROLE_CONTACT_OTHER = "contact_other"  # прочие контактные сведения

#: Роли, значения которых считаются контактными данными реестра НОСТРОЙ.
CONTACT_ROLES: frozenset[str] = frozenset(
    {ROLE_PHONE, ROLE_EMAIL, ROLE_ADDRESS, ROLE_DIRECTOR, ROLE_WEBSITE, ROLE_CONTACT_OTHER}
)

#: Роли, которые могут занимать только одну колонку (берём с максимальным весом).
SINGLE_VALUE_ROLES: frozenset[str] = frozenset(
    {ROLE_INN, ROLE_OGRN, ROLE_DATE_JOIN, ROLE_DATE_EXIT, ROLE_STATUS, ROLE_REG_NUMBER}
)


@dataclass(slots=True)
class RolePattern:
    """Шаблон сопоставления заголовка с ролью."""

    role: str
    pattern: str                    # регулярное выражение по нормализованному заголовку
    weight: float                   # чем выше, тем «увереннее» соответствие
    anti_pattern: str | None = None  # если совпало — соответствие отменяется

    def match(self, header: str) -> float:
        """Возвращает вес соответствия (0.0, если не подходит)."""
        if self.anti_pattern and re.search(self.anti_pattern, header):
            return 0.0
        return self.weight if re.search(self.pattern, header) else 0.0


#: Контакты САМОЙ СРО, а не её члена: «Телефон СРО», «Адрес места нахождения
#: саморегулируемой организации» и т.п. В выгрузках НОСТРОЙ такие колонки идут
#: рядом с контактами члена и одинаковы во всех строках — принимать их за
#: контакты компании нельзя.
#: Слово «СРО» должно стоять ПОСЛЕ названия контакта: иначе под шаблон попала бы
#: «шапка» вида «Реестр членов СРО | Телефон», где телефон принадлежит члену.
_SRO_CONTACT_ANTI = (
    r"(телефон|тел|адрес|почт|e ?mail|сайт|факс|руководител)"
    r"[а-яё ]{0,40}(сро|саморегулируем)"
)

#: Не-название: колонки СРО, банков, страховых, документов и т.п.
_NAME_ANTI = (
    r"наименовани[ея] сро|наименовани[ея] саморегулир|наименовани[ея] банка"
    r"|наименовани[ея] страхов|наименовани[ея] орган|наименовани[ея] документ"
    r"|наименовани[ея] вида|наименовани[ея] работ|наименовани[ея] программ"
    r"|наименовани[ея] учебн|наименовани[ея] объект|наименовани[ея] заказчик"
    r"|наименовани[ея] должност|сро$|^сро "
)

#: Полный набор правил «заголовок -> роль». Порядок не важен, важен вес.
ROLE_PATTERNS: tuple[RolePattern, ...] = (
    # ---------------------------- наименование ---------------------------- #
    RolePattern(ROLE_NAME, r"полное (фирменное )?наименование", 12, _NAME_ANTI),
    RolePattern(ROLE_NAME, r"наименование (члена|организации|юридического лица|юл|ип|компании)", 11, _NAME_ANTI),
    RolePattern(ROLE_NAME, r"^наименование$", 10, None),
    RolePattern(ROLE_NAME, r"^название$|^название организации$|^название компании$", 10, None),
    RolePattern(ROLE_NAME, r"сокращенное наименование|краткое наименование", 8, _NAME_ANTI),
    RolePattern(ROLE_NAME, r"^организация$|^компания$|^юридическое лицо$|^предприятие$", 8, None),
    RolePattern(ROLE_NAME, r"^фио$|^ф и о$|фамилия имя отчество|^ф$", 7, r"руководител|директор|специалист|контактн"),
    RolePattern(ROLE_NAME, r"член(а|ы|ов)? сро|наименование члена сро", 7, None),
    RolePattern(ROLE_NAME, r"наименование", 6, _NAME_ANTI),
    RolePattern(ROLE_NAME, r"^субъект( предпринимательской деятельности)?$", 6, None),
    RolePattern(ROLE_NAME, r"^контрагент$|^клиент$", 5, None),

    # -------------------------------- ИНН --------------------------------- #
    RolePattern(ROLE_INN, r"идентификационный номер налогоплательщика", 12, None),
    RolePattern(ROLE_INN, r"(^|\W)инн(\W|$)", 11, r"инн (банка|заказчика|страхов|поручител)"),
    RolePattern(ROLE_INN, r"^инн кпп$|^инн кпп члена", 10, None),

    # -------------------------------- ОГРН -------------------------------- #
    RolePattern(ROLE_OGRN, r"(^|\W)огрн(ип)?(\W|$)", 11, None),
    RolePattern(ROLE_OGRN, r"основной государственный регистрационный номер", 11, None),

    # ------------------------ дата вступления ------------------------------ #
    RolePattern(
        ROLE_DATE_JOIN,
        r"дата (вступления|приема|принятия|включения|внесения|начала членства|регистрации в реестре)",
        12,
        r"исключ|прекращ|выход|приостанов|возобновл|рожден",
    ),
    RolePattern(ROLE_DATE_JOIN, r"дата и номер решения о приеме", 11, r"исключ|прекращ"),
    RolePattern(ROLE_DATE_JOIN, r"(вступлени|прием в член|принят в член)", 9, r"исключ|прекращ|выход"),
    RolePattern(ROLE_DATE_JOIN, r"год вступления|членство с|дата начала", 8, r"исключ|прекращ|рожден"),
    RolePattern(ROLE_DATE_JOIN, r"^дата регистрации$|дата внесения сведений", 6, r"исключ|прекращ|рожден"),

    # ------------------------- дата исключения ---------------------------- #
    RolePattern(
        ROLE_DATE_EXIT,
        r"дата (исключения|прекращения|выхода|аннулирования|окончания членства)",
        12,
        r"рожден",
    ),
    RolePattern(
        ROLE_DATE_EXIT,
        r"решени[ияюе][^а-я]*(об?|о)\s*(исключени|прекращени|аннулировани|выход)",
        11,
        None,
    ),
    RolePattern(ROLE_DATE_EXIT, r"дата и номер решения об исключении", 11, None),
    RolePattern(ROLE_DATE_EXIT, r"(исключен|прекращени[ея] членства|выход из член)", 9, r"рожден"),
    RolePattern(ROLE_DATE_EXIT, r"членство по|дата окончания", 8, r"рожден"),

    # ------------------------------ статус --------------------------------- #
    RolePattern(ROLE_STATUS, r"^статус|статус членства|состояние членства|сведения о членстве", 9, None),
    RolePattern(ROLE_STATUS, r"действующ|прекращен(о|ное)? членство", 6, None),

    # ------------------------ реестровый номер ----------------------------- #
    RolePattern(ROLE_REG_NUMBER, r"регистрационный номер|реестровый номер|номер в реестре|номер записи", 9, None),

    # -------------------------------- СРО ---------------------------------- #
    RolePattern(ROLE_SRO, r"наименование сро|наименование саморегулируем|^сро$|^сро .*|саморегулируемая организация", 8, None),

    # ------------------------------ телефон -------------------------------- #
    RolePattern(ROLE_PHONE, r"(^|\W)(телефон|тел|тлф|моб|мобильный|факс)(\W|$)", 11, _SRO_CONTACT_ANTI),
    RolePattern(ROLE_PHONE, r"номер телефона|контактный телефон|телефоны", 11, _SRO_CONTACT_ANTI),

    # -------------------------------- email -------------------------------- #
    RolePattern(ROLE_EMAIL, r"e ?mail|электронн(ая|ой) почт|эл почт|адрес электронной почты", 12, _SRO_CONTACT_ANTI),
    RolePattern(ROLE_EMAIL, r"^почта$|^емайл$|^мейл$", 9, r"почтовый"),

    # -------------------------------- адрес -------------------------------- #
    RolePattern(
        ROLE_ADDRESS,
        r"(юридический|фактический|почтовый|полный|местонахождени|место нахождени)",
        10,
        r"электронн|сайт|e ?mail|" + _SRO_CONTACT_ANTI,
    ),
    RolePattern(ROLE_ADDRESS, r"(^|\W)адрес(\W|$)", 9, r"электронн|сайт|e ?mail|ip|" + _SRO_CONTACT_ANTI),
    RolePattern(ROLE_ADDRESS, r"место регистрации|место жительства|регион|субъект рф|индекс|город", 5, None),

    # ---------------------------- руководитель ----------------------------- #
    RolePattern(
        ROLE_DIRECTOR,
        r"(руководител|генеральный директор|^директор|единоличный исполнительный"
        r"|лицо имеющее право|президент|управляющ|глава)",
        11,
        _SRO_CONTACT_ANTI,
    ),
    RolePattern(ROLE_DIRECTOR, r"фио руководител|должность и фио", 12, None),

    # ------------------------------- сайт ---------------------------------- #
    RolePattern(ROLE_WEBSITE, r"(сайт|web|www|url|интернет ресурс)", 9, _SRO_CONTACT_ANTI),

    # -------------------- прочие контактные сведения ----------------------- #
    RolePattern(ROLE_CONTACT_OTHER, r"контакт|способ связи|мессенджер|whatsapp|telegram|viber", 7, None),
)

#: Заголовки, которые точно НЕ являются данными о члене СРО (порядковый номер и т.п.).
_SERVICE_HEADER_RE = re.compile(r"^(п ?п|n|№|номер п п|порядковый номер|id)$")


# --------------------------------------------------------------------------- #
#                              Карта колонок                                   #
# --------------------------------------------------------------------------- #

@dataclass(slots=True)
class ColumnMap:
    """Соответствие «роль -> индексы колонок» для конкретного листа."""

    headers: list[str] = field(default_factory=list)          # исходные заголовки
    normalized: list[str] = field(default_factory=list)       # нормализованные заголовки
    roles: dict[str, list[int]] = field(default_factory=dict)  # роль -> колонки (по убыванию веса)
    header_row: int | None = None                             # индекс строки шапки (0-based)
    header_span: int = 0                                      # сколько строк занимает шапка
    data_start_row: int = 0                                   # с какой строки начинаются данные
    detected_by: dict[str, str] = field(default_factory=dict)  # роль -> "заголовок"/"содержимое"

    # ------------------------------------------------------------------ #

    def first(self, role: str) -> int | None:
        """Индекс наиболее подходящей колонки для роли (или None)."""
        indexes = self.roles.get(role)
        return indexes[0] if indexes else None

    def all_of(self, role: str) -> list[int]:
        """Все колонки, отнесённые к роли."""
        return list(self.roles.get(role, ()))

    def contact_columns(self) -> list[tuple[int, str]]:
        """Все «контактные» колонки: ``[(индекс, роль), ...]``."""
        result: list[tuple[int, str]] = []
        for role in sorted(CONTACT_ROLES):
            for index in self.roles.get(role, ()):
                result.append((index, role))
        return sorted(set(result))

    def header_of(self, index: int) -> str:
        """Исходный заголовок колонки (или ``Колонка N``)."""
        if 0 <= index < len(self.headers) and self.headers[index]:
            return self.headers[index]
        return f"Колонка {index + 1}"

    @property
    def is_usable(self) -> bool:
        """Есть ли хотя бы название или ИНН — без них строка бесполезна."""
        return bool(self.roles.get(ROLE_NAME) or self.roles.get(ROLE_INN))

    def describe(self) -> str:
        """Краткое описание карты для лога."""
        parts = []
        for role, indexes in sorted(self.roles.items()):
            names = ", ".join(self.header_of(index) for index in indexes[:3])
            parts.append(f"{role}=[{names}]")
        return "; ".join(parts) if parts else "роли не определены"


# --------------------------------------------------------------------------- #
#                           Сопоставление заголовков                           #
# --------------------------------------------------------------------------- #

def match_header_roles(header: str) -> dict[str, float]:
    """
    Возвращает все роли, которым соответствует заголовок, с их весами.

    Одна колонка может подходить нескольким ролям (например, «Телефон, факс,
    email» — и телефон, и почта); учитываем все.
    """
    normalized = normalize_header(header)
    if not normalized or _SERVICE_HEADER_RE.match(normalized):
        return {}
    result: dict[str, float] = {}
    for rule in ROLE_PATTERNS:
        weight = rule.match(normalized)
        if weight > 0:
            result[rule.role] = max(result.get(rule.role, 0.0), weight)
    return result


def _combine_header_rows(rows: Sequence[Sequence[Any]]) -> list[str]:
    """
    Склеивает несколько строк шапки в один список заголовков.

    Верхние строки «протягиваются» вправо (объединённые ячейки в Excel дают
    значение только в левой ячейке диапазона), но только если в строке больше
    одной заполненной ячейки — иначе это заголовок-название листа, а не шапка.
    """
    if not rows:
        return []
    width = max(len(row) for row in rows)
    prepared: list[list[str]] = []
    for row_index, row in enumerate(rows):
        values = [cell_to_text(row[i]) if i < len(row) else "" for i in range(width)]
        is_last = row_index == len(rows) - 1
        non_empty = sum(1 for value in values if value)
        if not is_last and non_empty > 1:
            # Протягиваем значение объединённой ячейки вправо.
            last_value = ""
            for i, value in enumerate(values):
                if value:
                    last_value = value
                elif last_value:
                    values[i] = last_value
        elif not is_last and non_empty <= 1:
            # Единственная заполненная ячейка — это заголовок листа, не шапка.
            values = ["" for _ in values]
        prepared.append(values)

    combined: list[str] = []
    for column in range(width):
        parts: list[str] = []
        for row_values in prepared:
            value = row_values[column]
            if value and value not in parts:
                parts.append(value)
        combined.append(" ".join(parts).strip())
    return combined


def score_header_candidate(headers: Sequence[str]) -> tuple[float, dict[str, float]]:
    """
    Оценивает, насколько набор значений похож на строку заголовков.

    Возвращает ``(оценка, {роль: вес})``. Оценка учитывает:
    * число различных найденных ролей (главный фактор);
    * суммарный вес соответствий;
    * штраф за ячейки, похожие на данные (числа, даты, ИНН) — у настоящей
      шапки таких почти нет.
    """
    role_weights: dict[str, float] = {}
    matched_cells = 0
    data_like_cells = 0
    non_empty = 0

    for header in headers:
        text = clean_text(header)
        if not text:
            continue
        non_empty += 1
        roles = match_header_roles(text)
        if roles:
            matched_cells += 1
            for role, weight in roles.items():
                role_weights[role] = max(role_weights.get(role, 0.0), weight)
        # Признаки строки данных, а не шапки.
        if is_valid_inn(text) or parse_date(text) is not None:
            data_like_cells += 1
        elif re.fullmatch(r"[\d\s.,+()\-]+", text) and len(text) > 3:
            data_like_cells += 1

    if not role_weights:
        return 0.0, {}

    score = len(role_weights) * 10.0
    score += sum(role_weights.values()) / 10.0
    score += matched_cells
    score -= data_like_cells * 6.0
    # Наличие «якорных» ролей резко повышает уверенность.
    if ROLE_NAME in role_weights:
        score += 8.0
    if ROLE_INN in role_weights:
        score += 8.0
    if non_empty and matched_cells / non_empty >= 0.5:
        score += 5.0
    return score, role_weights


def detect_header_row(
    rows: Sequence[Sequence[Any]],
    scan_rows: int = 60,
    max_span: int = 3,
) -> tuple[int | None, int, list[str]]:
    """
    Ищет строку (или несколько строк) заголовков в начале листа.

    :return: ``(индекс первой строки шапки, число строк шапки, заголовки)``.
             Если шапку найти не удалось — ``(None, 0, [])``.
    """
    if not rows:
        return None, 0, []

    limit = min(scan_rows, len(rows))
    # Ключ сравнения: сначала оценка; при равной оценке — более короткая шапка
    # (склейка со строками-названиями над таблицей даёт тот же набор заголовков,
    # но настоящая шапка — только нижняя строка); при равной высоте — самая
    # ранняя (шапку часто дублируют ниже по листу, и это уже не начало таблицы).
    best_key: tuple[float, int, int] = (0.0, 0, 0)
    best: tuple[int | None, int, list[str]] = (None, 0, [])

    for start in range(limit):
        # «Многоэтажная» шапка оправдана, только если каждая добавленная строка
        # приносит НОВЫЕ роли (например, «Дата | вступления/исключения»).
        # Иначе на маленьких листах шапка «съедала» первую строку данных:
        # значения вроде «ИНН 5407123456» всё ещё похожи на заголовок с ИНН.
        roles_at_shorter_span = -1
        for span in range(1, max_span + 1):
            if start + span > len(rows):
                break
            headers = _combine_header_rows(rows[start : start + span])
            if not any(headers):
                continue
            score, roles = score_header_candidate(headers)
            # Шапка должна опознаваться минимум по двум ролям либо содержать ИНН.
            if len(roles) < 2 and ROLE_INN not in roles:
                continue
            if span > 1 and len(roles) <= roles_at_shorter_span:
                continue
            roles_at_shorter_span = max(roles_at_shorter_span, len(roles))
            key = (round(score, 6), -span, -start)
            if key > best_key:
                best_key = key
                best = (start, span, headers)

    if best[0] is None:
        return None, 0, []
    logger.debug("Шапка найдена: строка %s, высота %s, оценка %.1f", best[0] + 1, best[1], best_key[0])
    return best


# --------------------------------------------------------------------------- #
#                       Определение ролей по содержимому                       #
# --------------------------------------------------------------------------- #

@dataclass(slots=True)
class _ColumnStats:
    """Статистика значений одной колонки — основа автоопределения роли."""

    scanned: int = 0              # сколько строк просмотрено
    non_empty: int = 0
    inn: int = 0
    ogrn: int = 0
    dates: int = 0
    date_values: list[Any] = field(default_factory=list)
    phones: int = 0
    emails: int = 0
    addresses: int = 0
    company_names: int = 0
    org_markers: int = 0          # значения с явной организационно-правовой формой
    fio: int = 0
    urls: int = 0
    avg_length: float = 0.0

    def ratio(self, attribute: str) -> float:
        """Доля НЕПУСТЫХ значений колонки, подходящих под признак."""
        return getattr(self, attribute) / self.non_empty if self.non_empty else 0.0

    @property
    def fill_ratio(self) -> float:
        """Доля строк, где колонка вообще заполнена."""
        return self.non_empty / self.scanned if self.scanned else 0.0


def _collect_column_stats(
    rows: Sequence[Sequence[Any]],
    column: int,
    sample_size: int,
    date_mode: int,
) -> _ColumnStats:
    """Считает статистику по значениям одной колонки (не более ``sample_size`` штук)."""
    stats = _ColumnStats()
    total_length = 0
    for row in rows:
        if stats.non_empty >= sample_size:
            break
        stats.scanned += 1
        if column >= len(row):
            continue
        raw = row[column]
        text = clean_text(raw)
        if not text:
            continue
        stats.non_empty += 1
        total_length += len(text)

        if is_valid_inn(text) or (normalize_inn(text) and re.fullmatch(r"\d{10}|\d{12}", normalize_inn(text))):
            stats.inn += 1
        if re.fullmatch(r"\d{13}|\d{15}", re.sub(r"\D", "", text)):
            stats.ogrn += 1
        parsed = parse_date(raw, date_mode)
        if parsed is not None:
            stats.dates += 1
            stats.date_values.append(parsed)
        if extract_phones(text):
            stats.phones += 1
        if extract_emails(text):
            stats.emails += 1
        is_address = looks_like_address(text)
        if is_address:
            stats.addresses += 1
        # Адрес формально «похож на название» (буквы, длина), поэтому явно
        # исключаем его — иначе колонка адреса перехватит роль наименования.
        if not is_address and looks_like_company_name(text):
            stats.company_names += 1
        if not is_address and has_org_marker(text):
            stats.org_markers += 1
        if looks_like_fio(text):
            stats.fio += 1
        if re.search(r"https?://|www\.", text, re.IGNORECASE):
            stats.urls += 1

    stats.avg_length = total_length / stats.non_empty if stats.non_empty else 0.0
    return stats


def detect_roles_by_content(
    rows: Sequence[Sequence[Any]],
    column_map: ColumnMap,
    sample_size: int = 400,
    date_mode: int = 0,
) -> ColumnMap:
    """
    Дополняет карту колонок ролями, определёнными по самим данным.

    Вызывается всегда: и когда шапки нет вовсе, и когда шапка есть, но,
    например, колонка с ИНН названа нестандартно и не опозналась.
    Уже назначенные по заголовку роли не перезаписываются.
    """
    if not rows:
        return column_map

    width = max(len(row) for row in rows)
    assigned: set[int] = {index for indexes in column_map.roles.values() for index in indexes}
    stats_by_column: dict[int, _ColumnStats] = {}
    for column in range(width):
        stats_by_column[column] = _collect_column_stats(rows, column, sample_size, date_mode)

    def claim(role: str, column: int, source: str = "содержимое") -> None:
        """Назначает роль колонке, если роль ещё не занята."""
        column_map.roles.setdefault(role, [])
        if column not in column_map.roles[role]:
            column_map.roles[role].append(column)
        column_map.detected_by.setdefault(role, source)
        assigned.add(column)

    # --- ИНН: самый надёжный признак — контрольная сумма -------------------- #
    if not column_map.roles.get(ROLE_INN):
        candidates = [
            (column, stats.ratio("inn"))
            for column, stats in stats_by_column.items()
            if column not in assigned and stats.non_empty and stats.ratio("inn") >= 0.5
        ]
        if candidates:
            best_column = max(candidates, key=lambda item: item[1])[0]
            claim(ROLE_INN, best_column)
            logger.info("ИНН определён по содержимому: колонка %d", best_column + 1)

    # --- ОГРН --------------------------------------------------------------- #
    if not column_map.roles.get(ROLE_OGRN):
        candidates = [
            (column, stats.ratio("ogrn"))
            for column, stats in stats_by_column.items()
            if column not in assigned and stats.ratio("ogrn") >= 0.6
        ]
        if candidates:
            claim(ROLE_OGRN, max(candidates, key=lambda item: item[1])[0])

    # --- email / телефон / сайт / адрес ------------------------------------- #
    # Определяются раньше наименования: адрес формально похож на «текст с буквами»
    # и без этого мог бы перехватить роль названия компании.
    # Важно: одна колонка может нести сразу несколько видов контактов
    # («Телефон/e-mail», «Адрес, тел.»), поэтому проверяем занятость по
    # состоянию ДО этого цикла, а не по текущему.
    assigned_before_contacts = set(assigned)
    for role, attribute, threshold in (
        (ROLE_EMAIL, "emails", 0.4),
        (ROLE_PHONE, "phones", 0.4),
        (ROLE_WEBSITE, "urls", 0.4),
        (ROLE_ADDRESS, "addresses", 0.4),
    ):
        if column_map.roles.get(role):
            continue
        for column, stats in stats_by_column.items():
            if column in assigned_before_contacts or stats.non_empty == 0:
                continue
            if stats.ratio(attribute) >= threshold:
                claim(role, column)

    # --- наименование ------------------------------------------------------- #
    if not column_map.roles.get(ROLE_NAME):
        candidates = [
            (column, stats.ratio("org_markers"), stats.ratio("company_names"), stats.avg_length)
            for column, stats in stats_by_column.items()
            if column not in assigned and stats.non_empty and
            (stats.ratio("company_names") >= 0.5 or stats.ratio("fio") >= 0.6)
        ]
        if candidates:
            # Приоритет: явная орг.-правовая форма -> «похоже на название» -> длина.
            best_column = max(candidates, key=lambda item: (item[1], item[2], item[3]))[0]
            claim(ROLE_NAME, best_column)
            logger.info("Наименование определено по содержимому: колонка %d", best_column + 1)

    # --- даты вступления/исключения ----------------------------------------- #
    date_columns = [
        (column, stats)
        for column, stats in stats_by_column.items()
        if column not in assigned and stats.non_empty and stats.ratio("dates") >= 0.6
    ]
    # Дата вступления есть у КАЖДОГО члена СРО, поэтому колонка, заполненная
    # лишь у части строк, на эту роль не годится. Отсекает частый случай:
    # «Дата рождения» заполнена только у индивидуальных предпринимателей —
    # без этой проверки она становилась бы «датой вступления».
    dense_date_columns = [
        (column, stats) for column, stats in date_columns if stats.fill_ratio >= 0.5
    ]
    # Колонка с более ранними датами и большей заполненностью — «дата вступления».
    for group in (date_columns, dense_date_columns):
        group.sort(
            key=lambda item: (
                -item[1].non_empty,
                min(item[1].date_values) if item[1].date_values else _date.max,
            )
        )
    if not column_map.roles.get(ROLE_DATE_JOIN):
        if dense_date_columns:
            column, stats = dense_date_columns[0]
            date_columns = [item for item in date_columns if item[0] != column]
            claim(ROLE_DATE_JOIN, column)
            logger.info("Дата вступления определена по содержимому: колонка %d", column + 1)
        elif date_columns:
            logger.warning(
                "Колонка с датой вступления не найдена: ни один столбец с датами "
                "не заполнен хотя бы у половины записей. Проверьте заголовки файла"
            )
    if not column_map.roles.get(ROLE_DATE_EXIT) and date_columns:
        # Дата исключения заполнена реже даты вступления, но датой рождения
        # быть не может: отсекаем колонки, где даты заведомо «человеческие»
        # (медиана раньше 1960 года — так выглядят даты рождения ИП).
        def looks_like_birthdays(stats: _ColumnStats) -> bool:
            values = sorted(stats.date_values)
            if not values:
                return False
            median = values[len(values) // 2]
            return median.year < 1960

        candidates = [item for item in date_columns if not looks_like_birthdays(item[1])]
        if candidates:
            column, stats = min(candidates, key=lambda item: item[1].non_empty)
            claim(ROLE_DATE_EXIT, column)
            logger.info("Дата исключения определена по содержимому: колонка %d", column + 1)

    # --- руководитель -------------------------------------------------------- #
    if not column_map.roles.get(ROLE_DIRECTOR):
        for column, stats in stats_by_column.items():
            if column in assigned or stats.non_empty == 0:
                continue
            if stats.ratio("fio") >= 0.6:
                claim(ROLE_DIRECTOR, column)
                break

    return column_map


# --------------------------------------------------------------------------- #
#                             Сборка карты колонок                             #
# --------------------------------------------------------------------------- #

def build_column_map(
    rows: Sequence[Sequence[Any]],
    scan_rows: int = 60,
    max_span: int = 3,
    sample_size: int = 400,
    date_mode: int = 0,
) -> ColumnMap:
    """
    Полный цикл определения структуры листа.

    :param rows:        все строки листа «как есть»;
    :param scan_rows:   сколько верхних строк просматривать в поисках шапки;
    :param max_span:    максимальная высота «многоэтажной» шапки;
    :param sample_size: сколько значений колонки анализировать при автодетекте;
    :param date_mode:   система дат книги (для серийных чисел).
    """
    header_row, header_span, headers = detect_header_row(rows, scan_rows, max_span)
    column_map = ColumnMap(
        headers=list(headers),
        normalized=[normalize_header(header) for header in headers],
        header_row=header_row,
        header_span=header_span,
        data_start_row=(header_row + header_span) if header_row is not None else 0,
    )

    # --- роли по заголовкам -------------------------------------------------- #
    weighted: dict[str, list[tuple[float, int]]] = {}
    for index, header in enumerate(headers):
        for role, weight in match_header_roles(header).items():
            weighted.setdefault(role, []).append((weight, index))

    for role, items in weighted.items():
        items.sort(key=lambda item: (-item[0], item[1]))
        indexes = [index for _, index in items]
        if role in SINGLE_VALUE_ROLES:
            indexes = indexes[:1]
        column_map.roles[role] = indexes
        column_map.detected_by[role] = "заголовок"

    # Колонка, уже отнесённая к точной контактной роли (телефон/почта/адрес/...),
    # не должна дублироваться ещё и в «прочих контактах».
    specific_contacts = {
        index
        for role in (ROLE_PHONE, ROLE_EMAIL, ROLE_ADDRESS, ROLE_DIRECTOR, ROLE_WEBSITE)
        for index in column_map.roles.get(role, ())
    }
    if column_map.roles.get(ROLE_CONTACT_OTHER):
        remaining = [
            index for index in column_map.roles[ROLE_CONTACT_OTHER]
            if index not in specific_contacts
        ]
        if remaining:
            column_map.roles[ROLE_CONTACT_OTHER] = remaining
        else:
            column_map.roles.pop(ROLE_CONTACT_OTHER)
            column_map.detected_by.pop(ROLE_CONTACT_OTHER, None)

    # --- дополняем по содержимому -------------------------------------------- #
    data_rows = rows[column_map.data_start_row :] if rows else []
    detect_roles_by_content(data_rows or rows, column_map, sample_size, date_mode)

    logger.debug("Карта колонок: %s", column_map.describe())
    return column_map


def guess_headers_for_headerless(rows: Sequence[Sequence[Any]]) -> list[str]:
    """Формирует условные заголовки ``Колонка 1..N`` для листа без шапки."""
    width = max((len(row) for row in rows), default=0)
    return [f"Колонка {index + 1}" for index in range(width)]
