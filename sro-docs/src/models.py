# -*- coding: utf-8 -*-
"""Структура данных компании.

Единственный источник правды о реквизитах. Все значения — строки,
чтобы ИНН/ОГРН/счета никогда не теряли ведущие нули и не превращались
в научную нотацию.

Состав полей определён по РЕАЛЬНЫМ шаблонам (заявление + доверенность),
см. АНАЛИЗ_ШАБЛОНОВ.md. Поля, которые шаблонам не нужны, помечены
как `used_by_templates=False` — они парсятся и хранятся (пригодятся для
будущих документов СРО), но никогда не требуются для генерации.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields as dc_fields
from typing import Any


@dataclass
class FieldSpec:
    """Описание одного поля: как звать по-русски и насколько оно важно."""

    key: str
    label: str
    group: str
    used_by_templates: bool = True
    multiline: bool = False
    hint: str = ""


# Порядок здесь = порядок полей в интерфейсе.
FIELD_SPECS: list[FieldSpec] = [
    FieldSpec("full_name", "Полное наименование", "Организация",
              hint="Например: Общество с ограниченной ответственностью «Ромашка»"),
    FieldSpec("short_name", "Сокращённое наименование", "Организация",
              hint="Например: ООО «Ромашка»"),
    FieldSpec("inn", "ИНН", "Организация", hint="10 цифр для юридического лица"),
    FieldSpec("kpp", "КПП", "Организация", used_by_templates=False, hint="9 цифр"),
    FieldSpec("ogrn", "ОГРН", "Организация", hint="13 цифр"),
    FieldSpec("registration_date", "Дата регистрации", "Организация",
              used_by_templates=False),
    FieldSpec("legal_address", "Юридический адрес", "Адреса и связь", multiline=True),
    FieldSpec("actual_address", "Фактический адрес", "Адреса и связь", multiline=True,
              hint="Подставляется из юридического. Впишите свой, если адреса разные"),
    FieldSpec("postal_address", "Почтовый адрес", "Адреса и связь", multiline=True,
              hint="Подставляется из юридического. Впишите свой, если адреса разные"),
    FieldSpec("phone", "Телефон", "Адреса и связь", hint="Например: +7 (812) 123-45-67"),
    FieldSpec("email", "Электронная почта", "Адреса и связь"),
    FieldSpec("website", "Сайт", "Адреса и связь", used_by_templates=False),
    FieldSpec("director_position", "Должность руководителя", "Руководитель",
              hint="Как в Уставе: Генеральный директор, Директор, Президент…"),
    FieldSpec("director_full_name", "ФИО руководителя полностью", "Руководитель",
              hint="Именительный падеж: Иванов Иван Иванович"),
    FieldSpec("director_basis", "Основание полномочий", "Руководитель",
              hint="Обычно «Устав»"),
    FieldSpec("bank_name", "Наименование банка", "Банковские реквизиты",
              used_by_templates=False),
    FieldSpec("bank_account", "Расчётный счёт", "Банковские реквизиты",
              used_by_templates=False),
    FieldSpec("bank_corr_account", "Корреспондентский счёт", "Банковские реквизиты",
              used_by_templates=False),
    FieldSpec("bank_bik", "БИК", "Банковские реквизиты", used_by_templates=False),
    FieldSpec("okpo", "ОКПО", "Прочее", used_by_templates=False),
    FieldSpec("okato", "ОКАТО", "Прочее", used_by_templates=False),
]

FIELD_BY_KEY = {f.key: f for f in FIELD_SPECS}


@dataclass
class CompanyData:
    """Реквизиты ОДНОЙ компании.

    Каждая генерация документов работает со своим экземпляром — это
    архитектурная защита от подмешивания данных другой компании.
    """

    # --- Организация ---
    full_name: str = ""
    short_name: str = ""
    inn: str = ""
    kpp: str = ""
    ogrn: str = ""
    registration_date: str = ""

    # --- Адреса и связь ---
    legal_address: str = ""
    actual_address: str = ""
    postal_address: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""

    # --- Руководитель ---
    director_position: str = ""
    director_full_name: str = ""
    director_basis: str = ""

    # --- Банк (шаблонам не нужны, храним для будущих документов) ---
    bank_name: str = ""
    bank_account: str = ""
    bank_corr_account: str = ""
    bank_bik: str = ""

    # --- Прочее ---
    okpo: str = ""
    okato: str = ""

    # --- Параметры конкретного пакета документов (не реквизиты компании) ---
    doc_date: str = ""          # дата документов, ДД.ММ.ГГГГ
    power_number: str = ""      # номер доверенности; значение по умолчанию —
                                # в config/documents.json, раздел defaults
    object_kind: str = "ordinary"      # ordinary | hazardous | nuclear
    harm_fund_level: str = "1"         # уровень по п.12 ст.55.16 ГрК РФ
    contract_fund_level: str = ""      # уровень по п.13; пусто = КФ ОДО не заявляем

    # --- Подтверждённые пользователем склонения (перекрывают автоматику) ---
    overrides: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------
    def get(self, key: str) -> str:
        return str(getattr(self, key, "") or "")

    def set(self, key: str, value: Any) -> None:
        if hasattr(self, key):
            setattr(self, key, "" if value is None else str(value).strip())

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f in dc_fields(self):
            out[f.name] = getattr(self, f.name)
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompanyData":
        obj = cls()
        for f in dc_fields(cls):
            if f.name in data and data[f.name] is not None:
                value = data[f.name]
                if f.name == "overrides":
                    obj.overrides = dict(value)
                elif isinstance(value, (dict, list)):
                    continue
                else:
                    setattr(obj, f.name, str(value).strip())
        return obj

    def copy(self) -> "CompanyData":
        return CompanyData.from_dict(self.to_dict())

    def identity(self) -> str:
        """Короткая подпись компании — для логов и финальной сверки."""
        return f"{self.short_name or self.full_name} / ИНН {self.inn} / ОГРН {self.ogrn}"

    def is_empty(self) -> bool:
        return not any(self.get(f.key) for f in FIELD_SPECS)
