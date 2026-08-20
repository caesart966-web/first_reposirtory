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
    #: Поле есть только у одного типа заявителя: "company" или "entrepreneur".
    #: Пусто — поле нужно и юрлицу, и предпринимателю.
    only_for: str = ""


#: Тип заявителя. От него зависит длина ИНН и ОГРН, наличие КПП,
#: вид наименования и то, кто подписывает документы.
COMPANY = "company"
ENTREPRENEUR = "entrepreneur"

APPLICANT_KINDS = {
    COMPANY: "Юридическое лицо",
    ENTREPRENEUR: "Индивидуальный предприниматель",
}


# Порядок здесь = порядок полей в интерфейсе.
FIELD_SPECS: list[FieldSpec] = [
    FieldSpec("full_name", "Полное наименование", "Организация",
              hint="Например: Общество с ограниченной ответственностью «Ромашка»"),
    FieldSpec("short_name", "Сокращённое наименование", "Организация",
              hint="Например: ООО «Ромашка»"),
    FieldSpec("inn", "ИНН", "Организация", hint="10 цифр для юридического лица"),
    FieldSpec("kpp", "КПП", "Организация", used_by_templates=False, hint="9 цифр",
              only_for=COMPANY),
    FieldSpec("ogrn", "ОГРН", "Организация", hint="13 цифр"),
    FieldSpec("registration_date", "Дата регистрации", "Организация",
              used_by_templates=False),
    FieldSpec("legal_address", "Юридический адрес", "Адреса и связь", multiline=True),
    FieldSpec("actual_address", "Фактический адрес", "Адреса и связь", multiline=True,
              hint="Подставляется из юридического. Впишите свой, если адреса разные"),
    FieldSpec("postal_address", "Почтовый адрес", "Адреса и связь", multiline=True,
              hint="Подставляется из юридического. Впишите свой, если адреса разные"),
    FieldSpec("phone", "Телефон", "Адреса и связь", hint="Например: +7 (812) 123-45-67"),
    FieldSpec("email", "Электронная почта", "Адреса и связь",
              hint="Необязательно: если есть — впишите, без неё тоже можно"),
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

#: Параметры конкретного пакета документов — это НЕ реквизиты компании.
#: При разборе новой карточки они сохраняются, а не сбрасываются.
#: Список один на всю программу: раньше он был перечислен в двух местах
#: и разошёлся — номер заявления терялся.
#: Чем поля предпринимателя отличаются на вид. Сами поля те же —
#: меняются только название и подсказка, чтобы человек не гадал.
ENTREPRENEUR_LABELS = {
    "full_name": "ФИО предпринимателя полностью",
    "short_name": "Сокращённо",
    "ogrn": "ОГРНИП",
    "legal_address": "Адрес регистрации по месту жительства",
    "actual_address": "Адрес фактического осуществления деятельности",
    "director_position": "Должность подписанта",
    "director_full_name": "ФИО подписанта полностью",
}

ENTREPRENEUR_HINTS = {
    "full_name": "Например: Индивидуальный предприниматель Иванов Иван Иванович",
    "short_name": "Например: ИП Иванов И.И.",
    "inn": "12 цифр для индивидуального предпринимателя",
    "ogrn": "15 цифр (ОГРНИП)",
    "legal_address": "У предпринимателя обычно достаточно города прописки; "
                     "полный адрес — если он есть",
    "actual_address": "Обычно тот же город. Впишите свой, если отличается",
    "postal_address": "Обычно тот же город. Впишите свой, если отличается",
    "director_position": "Для предпринимателя это «Индивидуальный предприниматель»",
    "director_full_name": "Тот же человек, что и сам предприниматель",
    "director_basis": "У предпринимателя это лист записи ЕГРИП, а не Устав",
}

DOC_PARAM_FIELDS = (
    "doc_date", "doc_number", "power_number",
    "object_kind", "harm_fund_level", "contract_fund_level",
)

#: Умолчания для предпринимателя. Это подсказка в форме, а не подстановка
#: молча: человек видит значение и может его заменить.
ENTREPRENEUR_DEFAULTS = {
    "director_position": "Индивидуальный предприниматель",
    "director_basis": "Лист записи ЕГРИП",
}


@dataclass
class CompanyData:
    """Реквизиты ОДНОЙ компании.

    Каждая генерация документов работает со своим экземпляром — это
    архитектурная защита от подмешивания данных другой компании.
    """

    #: Юридическое лицо или индивидуальный предприниматель. От этого
    #: зависят длина ИНН и ОГРН, наличие КПП и вид наименования.
    applicant_kind: str = COMPANY

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
    power_number: str = ""      # номер доверенности; умолчание — в sro.json
    doc_number: str = ""        # исходящий номер заявления; умолчание — в sro.json
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
        return not any(self.get(f.key) for f in self.fields())

    # ------------------------------------------------------------------
    @property
    def is_entrepreneur(self) -> bool:
        return self.applicant_kind == ENTREPRENEUR

    def fields(self) -> list[FieldSpec]:
        """Поля, которые нужны ЭТОМУ заявителю.

        У предпринимателя нет КПП: спрашивать его — значит просить
        придумать несуществующий реквизит.
        """
        return [spec for spec in FIELD_SPECS
                if not spec.only_for or spec.only_for == self.applicant_kind]

    def hint_for(self, key: str) -> str:
        """Подсказка к полю с учётом типа заявителя."""
        if self.is_entrepreneur:
            special = ENTREPRENEUR_HINTS.get(key)
            if special:
                return special
        return FIELD_BY_KEY[key].hint if key in FIELD_BY_KEY else ""

    def label_for(self, key: str) -> str:
        """Название поля с учётом типа заявителя."""
        if self.is_entrepreneur:
            special = ENTREPRENEUR_LABELS.get(key)
            if special:
                return special
        return FIELD_BY_KEY[key].label if key in FIELD_BY_KEY else key
