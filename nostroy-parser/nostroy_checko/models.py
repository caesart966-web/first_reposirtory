"""
Модели данных.

Три уровня:

1. :class:`SourceRow`      — «сырая» строка конкретного листа конкретного файла;
2. :class:`RegistryRecord` — одна запись члена СРО, разобранная из строки;
3. :class:`CompanyGroup`   — объединение записей об одной и той же компании
   (ключ дедупликации) + результат запроса к checko.ru
   (:class:`CheckoContacts`).

Все классы умеют сериализоваться в JSON (``to_dict`` / ``from_dict``) —
это нужно для файла состояния, который позволяет продолжить работу
на следующий день, не потеряв уже собранное.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from .textutils import (
    clean_text,
    format_date,
    join_unique,
    merge_unique,
    normalize_company_name,
    parse_date,
)


# --------------------------------------------------------------------------- #
#                                Сырая строка                                  #
# --------------------------------------------------------------------------- #

@dataclass(slots=True)
class SourceRow:
    """Строка исходной таблицы вместе с её «координатами»."""

    file_path: str          # путь к файлу-источнику (относительный, для отчёта)
    sheet_name: str         # имя листа
    row_number: int         # номер строки в листе, начиная с 1 (как в Excel)
    values: list[Any]       # значения ячеек в порядке колонок
    headers: list[str]      # заголовки колонок (могут быть пустыми строками)

    @property
    def location(self) -> str:
        """Человекочитаемая ссылка на источник: ``файл.xlsx | Лист1 | строка 42``."""
        return f"{self.file_path} | {self.sheet_name} | строка {self.row_number}"

    def as_mapping(self) -> dict[str, str]:
        """Словарь ``{заголовок: значение}`` — для колонки «все поля реестра»."""
        result: dict[str, str] = {}
        for index, value in enumerate(self.values):
            header = self.headers[index] if index < len(self.headers) else ""
            key = header or f"Колонка {index + 1}"
            text = clean_text(value)
            if text:
                # Одинаковые заголовки не должны затирать друг друга.
                if key in result:
                    key = f"{key} ({index + 1})"
                result[key] = text
        return result


# --------------------------------------------------------------------------- #
#                            Запись реестра НОСТРОЙ                            #
# --------------------------------------------------------------------------- #

@dataclass(slots=True)
class RegistryRecord:
    """
    Одна запись члена СРО из реестра НОСТРОЙ.

    Поля, которые требуется извлечь по ТЗ: наименование, ИНН, дата вступления,
    дата исключения и любые контактные данные из самого реестра.
    """

    name: str = ""                                   # Название компании / ИП / ФИО
    inn: str = ""                                    # ИНН (10 или 12 цифр)
    ogrn: str = ""                                   # ОГРН/ОГРНИП, если есть
    date_join: date | None = None                    # Дата вступления в СРО
    date_exit: date | None = None                    # Дата исключения (None, если действующий)
    status: str = ""                                 # Статус членства из реестра
    reg_number: str = ""                             # Регистрационный номер в реестре
    sro_name: str = ""                               # Название СРО (СРО-С-410-... и т.п.)

    # --- контакты из самого реестра ---------------------------------------- #
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    directors: list[str] = field(default_factory=list)
    websites: list[str] = field(default_factory=list)
    other_contacts: dict[str, str] = field(default_factory=dict)   # прочие «контактные» колонки

    # --- служебное ---------------------------------------------------------- #
    source_file: str = ""
    source_sheet: str = ""
    source_row: int = 0
    raw_fields: dict[str, str] = field(default_factory=dict)       # вся строка целиком
    warnings: list[str] = field(default_factory=list)              # что не удалось распознать

    # ------------------------------------------------------------------ #

    @property
    def location(self) -> str:
        """Ссылка на источник записи."""
        return f"{self.source_file} | {self.sheet_name_safe} | строка {self.source_row}"

    @property
    def sheet_name_safe(self) -> str:
        return self.source_sheet or "?"

    @property
    def has_identity(self) -> bool:
        """Есть ли хоть что-то, по чему запись можно опознать (ИНН или название)."""
        return bool(self.inn or self.name)

    def dedupe_key(self, mode: str = "inn") -> str:
        """
        Ключ дедупликации.

        * ``inn``      — по ИНН (одинаковый ИНН = одно юрлицо = один запрос к checko);
          если ИНН нет, ключ строится по нормализованному названию;
        * ``name_inn`` — буквально по паре «Название + ИНН» (как в ТЗ);
          вариант расходует больше суточной квоты при разных написаниях названия.
        """
        normalized_name = normalize_company_name(self.name)
        if mode == "name_inn":
            return f"name_inn:{normalized_name}|{self.inn}"
        if self.inn:
            return f"inn:{self.inn}"
        return f"name:{normalized_name}"

    # ------------------------- сериализация --------------------------- #

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "inn": self.inn,
            "ogrn": self.ogrn,
            "date_join": self.date_join.isoformat() if self.date_join else None,
            "date_exit": self.date_exit.isoformat() if self.date_exit else None,
            "status": self.status,
            "reg_number": self.reg_number,
            "sro_name": self.sro_name,
            "phones": self.phones,
            "emails": self.emails,
            "addresses": self.addresses,
            "directors": self.directors,
            "websites": self.websites,
            "other_contacts": self.other_contacts,
            "source_file": self.source_file,
            "source_sheet": self.source_sheet,
            "source_row": self.source_row,
            "raw_fields": self.raw_fields,
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegistryRecord":
        return cls(
            name=data.get("name", ""),
            inn=data.get("inn", ""),
            ogrn=data.get("ogrn", ""),
            date_join=parse_date(data.get("date_join")),
            date_exit=parse_date(data.get("date_exit")),
            status=data.get("status", ""),
            reg_number=data.get("reg_number", ""),
            sro_name=data.get("sro_name", ""),
            phones=list(data.get("phones", [])),
            emails=list(data.get("emails", [])),
            addresses=list(data.get("addresses", [])),
            directors=list(data.get("directors", [])),
            websites=list(data.get("websites", [])),
            other_contacts=dict(data.get("other_contacts", {})),
            source_file=data.get("source_file", ""),
            source_sheet=data.get("source_sheet", ""),
            source_row=int(data.get("source_row", 0) or 0),
            raw_fields=dict(data.get("raw_fields", {})),
            warnings=list(data.get("warnings", [])),
        )


# --------------------------------------------------------------------------- #
#                            Результат checko.ru                               #
# --------------------------------------------------------------------------- #

#: Статусы результата запроса к checko.ru.
STATUS_OK = "ok"                    # карточка найдена и разобрана
STATUS_NOT_FOUND = "not_found"      # компания не найдена (404 / пустой поиск)
STATUS_FORBIDDEN = "forbidden"      # 403 — доступ закрыт (блокировка/капча)
STATUS_RATE_LIMITED = "rate_limited"  # 429 — исчерпан лимит запросов
STATUS_ERROR = "error"              # сетевая ошибка / 5xx / неразобранный ответ
STATUS_SKIPPED = "skipped"          # запрос не делался (кончилась квота и т.п.)


@dataclass(slots=True)
class CheckoContacts:
    """Контактные данные компании, собранные со страницы checko.ru."""

    query: str = ""                  # что искали (ИНН или название)
    status: str = STATUS_SKIPPED     # см. константы STATUS_*
    source: str = ""                 # чем получено: "api" или "html"
    url: str = ""                    # адрес карточки компании
    http_status: int | None = None   # код последнего HTTP-ответа
    error: str = ""                  # текст ошибки, если была

    name: str = ""                   # наименование по данным checko
    inn: str = ""                    # ИНН по данным checko (проверка совпадения)
    ogrn: str = ""
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    directors: list[str] = field(default_factory=list)   # ФИО руководителя (+должность)
    websites: list[str] = field(default_factory=list)
    extra: dict[str, str] = field(default_factory=dict)  # прочие поля карточки

    inn_matched: bool | None = None  # совпал ли ИНН на странице с запрошенным
    fetched_at: str = ""             # ISO-время получения данных
    attempts: int = 0                # сколько раз пытались получить карточку
    quota_used: int = 0              # сколько единиц суточной квоты потрачено

    @property
    def is_success(self) -> bool:
        """Успешен ли результат (карточка получена)."""
        return self.status == STATUS_OK

    @property
    def is_final(self) -> bool:
        """
        Окончательный ли результат.

        ``ok`` и ``not_found`` повторять не нужно; ошибки/лимиты — нужно
        (при следующем запуске или по ключу ``--retry-failed``).
        """
        return self.status in (STATUS_OK, STATUS_NOT_FOUND)

    @property
    def has_contacts(self) -> bool:
        return bool(self.phones or self.emails or self.addresses or self.directors)

    def contacts_summary(self) -> str:
        """Все контакты одной строкой — для сводной вкладки отчёта."""
        parts: list[str] = []
        if self.phones:
            parts.append("тел.: " + join_unique(self.phones))
        if self.emails:
            parts.append("email: " + join_unique(self.emails))
        if self.addresses:
            parts.append("адрес: " + join_unique(self.addresses))
        if self.directors:
            parts.append("рук.: " + join_unique(self.directors))
        return " | ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "status": self.status,
            "source": self.source,
            "url": self.url,
            "http_status": self.http_status,
            "error": self.error,
            "name": self.name,
            "inn": self.inn,
            "ogrn": self.ogrn,
            "phones": self.phones,
            "emails": self.emails,
            "addresses": self.addresses,
            "directors": self.directors,
            "websites": self.websites,
            "extra": self.extra,
            "inn_matched": self.inn_matched,
            "fetched_at": self.fetched_at,
            "attempts": self.attempts,
            "quota_used": self.quota_used,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CheckoContacts":
        return cls(
            query=data.get("query", ""),
            status=data.get("status", STATUS_SKIPPED),
            source=data.get("source", ""),
            url=data.get("url", ""),
            http_status=data.get("http_status"),
            error=data.get("error", ""),
            name=data.get("name", ""),
            inn=data.get("inn", ""),
            ogrn=data.get("ogrn", ""),
            phones=list(data.get("phones", [])),
            emails=list(data.get("emails", [])),
            addresses=list(data.get("addresses", [])),
            directors=list(data.get("directors", [])),
            websites=list(data.get("websites", [])),
            extra=dict(data.get("extra", {})),
            inn_matched=data.get("inn_matched"),
            fetched_at=data.get("fetched_at", ""),
            attempts=int(data.get("attempts", 0) or 0),
            quota_used=int(data.get("quota_used", 0) or 0),
        )


# --------------------------------------------------------------------------- #
#                       Группа записей об одной компании                       #
# --------------------------------------------------------------------------- #

@dataclass(slots=True)
class CompanyGroup:
    """
    Все записи реестра, относящиеся к одной компании, плюс данные с checko.ru.

    Дубликаты в реестрах — норма (компания встречается в нескольких файлах,
    листах и выгрузках), поэтому запрос к checko делается один раз на группу,
    а в отчёт попадают объединённые данные всех вхождений.
    """

    key: str                                          # ключ дедупликации
    records: list[RegistryRecord] = field(default_factory=list)
    checko: CheckoContacts | None = None
    #: Даты/статус из открытого реестра НОСТРОЙ (если файл выгрузки их не содержит).
    nostroy_date_join: date | None = None
    nostroy_date_exit: date | None = None
    nostroy_status: str = ""
    nostroy_phones: list[str] = field(default_factory=list)
    nostroy_emails: list[str] = field(default_factory=list)
    nostroy_addresses: list[str] = field(default_factory=list)
    nostroy_directors: list[str] = field(default_factory=list)

    # ------------------------- сводные поля --------------------------- #

    @property
    def name(self) -> str:
        """Самое информативное (самое длинное) написание названия."""
        names = [r.name for r in self.records if r.name]
        return max(names, key=len) if names else ""

    @property
    def all_names(self) -> list[str]:
        """Все встреченные варианты написания названия."""
        result: list[str] = []
        for record in self.records:
            if record.name and record.name not in result:
                result.append(record.name)
        return result

    @property
    def inn(self) -> str:
        for record in self.records:
            if record.inn:
                return record.inn
        return ""

    @property
    def ogrn(self) -> str:
        for record in self.records:
            if record.ogrn:
                return record.ogrn
        return ""

    @property
    def date_join(self) -> date | None:
        """Дата вступления: из файла выгрузки, а если там нет — из реестра НОСТРОЙ."""
        dates = [r.date_join for r in self.records if r.date_join]
        return min(dates) if dates else self.nostroy_date_join

    @property
    def date_exit(self) -> date | None:
        """Дата исключения: из файла выгрузки, а если там нет — из реестра НОСТРОЙ."""
        dates = [r.date_exit for r in self.records if r.date_exit]
        return max(dates) if dates else self.nostroy_date_exit

    @property
    def status(self) -> str:
        """Статус членства так, как он записан в реестре (текст как есть)."""
        return next((r.status for r in self.records if r.status), "")

    @property
    def membership_status(self) -> str:
        """
        Короткий статус членства для сортировки: ``действует`` или ``исключён``.

        Определяющий признак — дата исключения: она же стоит в соседней колонке
        отчёта, и расхождение между ними сбивало бы с толку. Если даты нет,
        смотрим текст статуса из реестра («прекращено членство», «исключён»
        и подобные формулировки). В остальных случаях компания считается
        действующей.
        """
        if self.date_exit is not None:
            return "исключён"
        text = (self.status or self.nostroy_status).lower().replace("ё", "е")
        if re.search(r"исключ|прекращ|выход|аннулир|не явля", text):
            return "исключён"
        return "действует"

    @property
    def sro_names(self) -> list[str]:
        result: list[str] = []
        for record in self.records:
            if record.sro_name and record.sro_name not in result:
                result.append(record.sro_name)
        return result

    def _collect(self, attribute: str) -> list[str]:
        """Объединяет одноимённые списки контактов из всех записей группы."""
        result: list[str] = []
        for record in self.records:
            merge_unique(result, getattr(record, attribute))
        return result

    @property
    def registry_phones(self) -> list[str]:
        return self._collect("phones")

    @property
    def registry_emails(self) -> list[str]:
        return self._collect("emails")

    @property
    def registry_addresses(self) -> list[str]:
        return self._collect("addresses")

    @property
    def registry_directors(self) -> list[str]:
        return self._collect("directors")

    @property
    def registry_websites(self) -> list[str]:
        return self._collect("websites")

    @property
    def registry_other_contacts(self) -> dict[str, str]:
        merged: dict[str, str] = {}
        for record in self.records:
            for key, value in record.other_contacts.items():
                if value and merged.get(key) != value:
                    merged[key] = value if key not in merged else f"{merged[key]}; {value}"
        return merged

    # --- объединение контактов реестра и checko ------------------------ #

    @property
    def all_phones(self) -> list[str]:
        result = list(self.registry_phones)
        if self.checko:
            merge_unique(result, self.checko.phones)
        return result

    @property
    def all_emails(self) -> list[str]:
        result = list(self.registry_emails)
        if self.checko:
            merge_unique(result, self.checko.emails)
        return result

    @property
    def all_addresses(self) -> list[str]:
        result = list(self.registry_addresses)
        if self.checko:
            merge_unique(result, self.checko.addresses)
        return result

    @property
    def all_directors(self) -> list[str]:
        result = list(self.registry_directors)
        if self.checko:
            merge_unique(result, self.checko.directors)
        return result

    # --- «лучшее из доступного»: checko, а если пусто — реестр ---------- #
    # Реестр НОСТРОЙ часто содержит адрес и руководителя, а иногда телефон и
    # почту. Ждать их с checko.ru незачем: данные уже есть и не зависят от
    # суточной квоты. Поэтому в отчёт идёт значение с checko, а при его
    # отсутствии — значение из реестра. Так таблица полезна с первого дня,
    # даже если сервис недоступен.

    def _best(self, checko_values: list[str], attribute: str, nostroy_values: list[str]) -> list[str]:
        """Объединяет источники: checko -> файл выгрузки -> реестр НОСТРОЙ."""
        result: list[str] = []
        merge_unique(result, checko_values)
        merge_unique(result, self._collect(attribute))
        merge_unique(result, nostroy_values)
        return result

    @property
    def best_phones(self) -> list[str]:
        return self._best(self.checko.phones if self.checko else [], "phones", self.nostroy_phones)

    @property
    def best_emails(self) -> list[str]:
        return self._best(self.checko.emails if self.checko else [], "emails", self.nostroy_emails)

    @property
    def best_addresses(self) -> list[str]:
        # Адрес показываем один, самый информативный: checko свежее, файл и
        # реестр НОСТРОЙ — запасные. Склейка трёх адресов сбивала бы с толку.
        for values in (
            self.checko.addresses if self.checko else [],
            self.registry_addresses,
            self.nostroy_addresses,
        ):
            if values:
                return values
        return []

    @property
    def best_directors(self) -> list[str]:
        for values in (
            self.checko.directors if self.checko else [],
            self.registry_directors,
            self.nostroy_directors,
        ):
            if values:
                return values
        return []

    @property
    def sources(self) -> list[str]:
        """Список всех источников (файл | лист | строка), где встретилась компания."""
        result: list[str] = []
        for record in self.records:
            location = record.location
            if location not in result:
                result.append(location)
        return result

    @property
    def checko_status(self) -> str:
        return self.checko.status if self.checko else STATUS_SKIPPED

    def registry_contacts_summary(self) -> str:
        """Контакты из реестра НОСТРОЙ одной строкой."""
        parts: list[str] = []
        if self.registry_phones:
            parts.append("тел.: " + join_unique(self.registry_phones))
        if self.registry_emails:
            parts.append("email: " + join_unique(self.registry_emails))
        if self.registry_addresses:
            parts.append("адрес: " + join_unique(self.registry_addresses))
        if self.registry_directors:
            parts.append("рук.: " + join_unique(self.registry_directors))
        return " | ".join(parts)

    def query_for_checko(self) -> str:
        """Строка запроса к checko.ru: предпочтительно ИНН, иначе название."""
        return self.inn or self.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "records": [record.to_dict() for record in self.records],
            "checko": self.checko.to_dict() if self.checko else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompanyGroup":
        return cls(
            key=data["key"],
            records=[RegistryRecord.from_dict(item) for item in data.get("records", [])],
            checko=CheckoContacts.from_dict(data["checko"]) if data.get("checko") else None,
        )


# --------------------------------------------------------------------------- #
#                       Нераспознанные строки (диагностика)                    #
# --------------------------------------------------------------------------- #

@dataclass(slots=True)
class UnrecognizedRow:
    """
    Строка, из которой не удалось извлечь ни ИНН, ни названия.

    Такие строки НЕ выбрасываются молча: они выгружаются в
    ``output/parsed/unrecognized_rows.csv`` (и, по ключу ``--with-diagnostics``,
    на отдельную вкладку отчёта), чтобы оператор мог их проверить глазами.
    """

    file_path: str
    sheet_name: str
    row_number: int
    reason: str
    preview: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "Файл": self.file_path,
            "Лист": self.sheet_name,
            "Строка": self.row_number,
            "Причина": self.reason,
            "Содержимое строки": self.preview,
        }


def utcnow_iso() -> str:
    """Текущее время в ISO-формате (для отметок в состоянии и отчёте)."""
    return datetime.now().replace(microsecond=0).isoformat()


def date_to_str(value: date | None) -> str:
    """Обёртка над :func:`format_date` для удобного импорта из отчёта."""
    return format_date(value)
