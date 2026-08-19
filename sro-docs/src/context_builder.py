# -*- coding: utf-8 -*-
"""Сборка значений переменных для подстановки в шаблоны.

Здесь и только здесь реквизиты компании превращаются в то, что реально
попадёт в документ: разбитые по клеткам цифры ИНН, родительный падеж ФИО,
отметки «V», дата прописью.

Если склонение вызывает сомнения, значение НЕ подставляется молча:
собирается список подтверждений (`Confirmation`), которые интерфейс
показывает пользователю.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from . import morphology
from .company_parser import split_company_name
from .models import CompanyData

MARK = "V"
MARK_LEVEL = "v"

OBJECT_KINDS = {
    "ordinary": "Объекты капитального строительства (кроме особо опасных, "
                "технически сложных и уникальных)",
    "hazardous": "Особо опасные, технически сложные и уникальные объекты",
    "nuclear": "Объекты использования атомной энергии",
}

@dataclass
class Confirmation:
    """Значение, которое программа не смогла определить надёжно."""

    key: str            # ключ в company.overrides
    label: str          # что подтверждаем, по-русски
    suggestion: str     # что предлагает программа
    reason: str         # почему нужна проверка


@dataclass
class ContextResult:
    values: dict[str, str] = field(default_factory=dict)
    confirmations: list[Confirmation] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


#: С чего начинается «домовая» часть адреса. Порядок важен: сначала длинные.
HOUSE_MARKERS = (
    "владение", "домовладение", "дом ", "д.", "корпус", "корп.", "корп ",
    "строение", "стр.", "стр ", "литера", "лит.", "помещение", "помещ.",
    "пом.", "офис", "оф.", "квартира", "кв.", "этаж", "комната", "ком.",
)


def split_address(address: str) -> tuple[str, str]:
    """Разделить адрес на «до дома» и «дом и далее».

    Некоторые бланки просят адрес двумя строками: сверху индекс, регион,
    город и улица, снизу — номер дома, корпуса и офиса. Делим по первому
    указателю дома.

    Если указателя нет, весь адрес уходит в первую строку, вторая остаётся
    пустой: выдумывать разбиение нельзя.
    """
    text = (address or "").strip()
    if not text:
        return "", ""
    lowered = text.lower()
    best = None
    for marker in HOUSE_MARKERS:
        position = lowered.find(marker)
        if position <= 0:
            continue
        # Указатель должен начинать слово, а не сидеть внутри другого.
        if text[position - 1].isalnum():
            continue
        if best is None or position < best:
            best = position
    if best is None:
        return text, ""
    head = text[:best].rstrip().rstrip(",").rstrip()
    tail = text[best:].strip()
    return head, tail


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _parse_date(value: str) -> date | None:
    match = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", (value or "").strip())
    if not match:
        return None
    day, month, year = (int(x) for x in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _resolve(company: CompanyData, key: str, computed: morphology.Inflected,
             label: str, result: ContextResult) -> str:
    """Взять подтверждённое пользователем значение либо запросить подтверждение."""
    override = (company.overrides or {}).get(key, "").strip()
    if override:
        return override
    if computed.confident or not computed.value:
        return computed.value
    result.confirmations.append(
        Confirmation(key, label, computed.value,
                     computed.reason or "автоматическое склонение ненадёжно")
    )
    return computed.value


def build_context(company: CompanyData, attorney: dict[str, str],
                  today: date | None = None, sro=None) -> ContextResult:
    """Собрать все значения переменных для одной компании.

    `sro` — профиль саморегулируемой организации: из него берутся
    переменные {{sro_name}}, {{sro_short_name}}, {{sro_city}}.
    """
    result = ContextResult()
    values = result.values

    # ---------------------------------------------------------- сама СРО
    values["sro_name"] = getattr(sro, "name", "") or ""
    values["sro_short_name"] = getattr(sro, "short_name", "") or ""
    values["sro_city"] = getattr(sro, "city", "") or ""

    # ---------------------------------------------------------- наименования
    form_short_full, form_full, bare_full = split_company_name(company.full_name)
    form_short, _, bare_short = split_company_name(company.short_name)

    values["legal_form_full"] = form_full or form_short_full
    values["company_name_bare"] = bare_full
    values["legal_form_short"] = form_short or form_short_full
    values["short_name_bare"] = bare_short
    # Наименования целиком — нужны бланкам, где для них одна строка.
    values["company_full_name"] = company.full_name
    values["company_short_name"] = company.short_name

    if company.full_name and not values["legal_form_full"]:
        result.notes.append(
            f"В полном наименовании «{company.full_name}» не распознана "
            f"организационно-правовая форма (ООО, АО, ПАО…). Проверьте написание."
        )
    if company.short_name and not values["legal_form_short"]:
        result.notes.append(
            f"В сокращённом наименовании «{company.short_name}» не распознана "
            f"организационно-правовая форма (ООО, АО, ПАО…). Проверьте написание."
        )
    if company.is_entrepreneur:
        result.notes.append(
            "Заявитель — индивидуальный предприниматель. Бланки СРО напечатаны "
            "под юридическое лицо, поэтому в них останутся слова «юридического "
            "лица» и «организации». Программа подставит ваши данные, добавит "
            "недостающие клетки под 12-значный ИНН и 15-значный ОГРНИП, но "
            "перед подачей обязательно просмотрите готовые документы."
        )
    elif values["legal_form_short"] and values["legal_form_short"] != "ООО":
        result.notes.append(
            f"Бланки СРО напечатаны под ООО, а у вас {values['legal_form_short']}. "
            f"Программа подставит вашу форму собственности, но перед подачей "
            f"обязательно просмотрите готовые документы."
        )

    # ---------------------------------------------------------- идентификаторы
    inn = _digits(company.inn)
    ogrn = _digits(company.ogrn)
    values["inn"] = inn
    values["ogrn"] = ogrn
    # У предпринимателя КПП не бывает: подставляем пустоту, а не выдумываем.
    values["kpp"] = "" if company.is_entrepreneur else _digits(company.kpp)
    # Там, где КПП вписан прямо в предложение бланка, у предпринимателя
    # должен выпасть весь оборот, а не остаться «КПП ,» с пустым местом.
    values["kpp_phrase"] = f"КПП {values['kpp']}, " if values["kpp"] else ""
    # Клеток в бланках бывает разное число: у юрлица ИНН 10 знаков и ОГРН 13,
    # у предпринимателя — 12 и 15. Бланк ЯРД рассчитан на предпринимателя,
    # поэтому клеток больше. Заполняем слева направо, лишние остаются пустыми.
    for index in range(12):
        values[f"inn_d{index + 1}"] = inn[index] if index < len(inn) else ""
    for index in range(15):
        values[f"ogrn_d{index + 1}"] = ogrn[index] if index < len(ogrn) else ""

    # ---------------------------------------------------------- адреса и связь
    values["legal_address"] = company.legal_address
    values["actual_address"] = company.actual_address
    values["postal_address"] = company.postal_address
    # Бланки, где адрес просят двумя строками: улица сверху, дом снизу.
    for name in ("legal_address", "actual_address", "postal_address"):
        street, house = split_address(company.get(name))
        values[f"{name}_street"] = street
        values[f"{name}_house"] = house
    values["phone"] = company.phone
    values["email"] = company.email
    values["website"] = company.website

    # ---------------------------------------------------------- банк
    values["bank_name"] = company.bank_name
    values["bank_account"] = _digits(company.bank_account)
    values["bank_corr_account"] = _digits(company.bank_corr_account)
    values["bank_bik"] = _digits(company.bank_bik)

    # ---------------------------------------------------------- руководитель
    full_name = company.director_full_name
    values["director_position"] = company.director_position
    values["director_full_name"] = full_name

    values["director_short_name"] = _resolve(
        company, "director_short_name", morphology.short_name(full_name),
        "Подпись руководителя (Фамилия И.О.)", result)

    # Некоторые бланки просят подпись в обратном порядке: «И.О. Фамилия».
    # Переставляем уже готовое (и при необходимости подтверждённое
    # пользователем) значение, а не разбираем ФИО заново.
    short_parts = values["director_short_name"].split(" ", 1)
    values["director_initials_name"] = (
        f"{short_parts[1]} {short_parts[0]}" if len(short_parts) == 2
        else values["director_short_name"])

    values["director_full_name_genitive"] = _resolve(
        company, "director_full_name_genitive", morphology.full_name_genitive(full_name),
        f"ФИО руководителя в родительном падеже («в лице …»)", result)

    values["director_position_genitive"] = _resolve(
        company, "director_position_genitive",
        morphology.position_genitive(company.director_position),
        "Должность руководителя в родительном падеже («в лице …»)", result)

    values["director_basis_genitive"] = _resolve(
        company, "director_basis_genitive",
        morphology.basis_genitive(company.director_basis),
        "Основание полномочий в родительном падеже («на основании …»)", result)

    # ---------------------------------------------------------- дата документа
    doc_date = _parse_date(company.doc_date) or (today or date.today())
    values["doc_day"] = f"{doc_date.day:02d}"
    values["doc_month_name"] = morphology.MONTHS_GENITIVE[doc_date.month - 1]
    values["doc_year"] = str(doc_date.year)
    values["doc_date"] = doc_date.strftime("%d.%m.%Y")

    values["power_number"] = company.power_number
    values["doc_number"] = company.doc_number

    # ---------------------------------------------------------- строки контактов
    # Некоторые бланки просят контакты одной строкой в заданном порядке.
    # Собираем ровно из того, что есть; пустые части просто пропускаем.
    def joined(*parts: str) -> str:
        return ", ".join(part for part in parts if part and part.strip())

    values["director_contact_line"] = joined(
        company.director_full_name, company.director_position,
        company.phone, company.email)
    values["company_contact_line"] = joined(
        company.phone, company.email, company.website)

    # ---------------------------------------------------------- отметки «V»
    for kind in OBJECT_KINDS:
        values[f"mark_object_{kind}"] = MARK if company.object_kind == kind else ""
    for level in "12345":
        values[f"mark_harm_level{level}"] = (
            MARK_LEVEL if company.harm_fund_level == level else "")
        values[f"mark_contract_level{level}"] = (
            MARK_LEVEL if company.contract_fund_level == level else "")

    # ------------------------------------------- участие в конкурентных закупках
    # Бланк СИС спрашивает словом «ДА» или «НЕТ». Это не отдельный вопрос
    # к пользователю: участие в конкурентных закупках и есть то, ради чего
    # вступают в компенсационный фонд обеспечения договорных обязательств.
    # Выбран уровень такого фонда — «ДА», не выбран — «НЕТ».
    values["contract_participation"] = "ДА" if company.contract_fund_level else "НЕТ"

    # ---------------------------------------------------------- представитель
    for key, value in attorney.items():
        values[key] = value

    return result
