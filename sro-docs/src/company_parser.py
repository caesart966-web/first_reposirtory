# -*- coding: utf-8 -*-
"""Извлечение реквизитов компании из карточки или произвольного текста.

Парсер работает по двум каналам:
  1) пары «подпись → значение» (таблицы DOCX/XLSX) — самый надёжный источник;
  2) построчный разбор текста вида «Подпись: значение» и поиск по образцам.

Ничего не выдумывает. Если значение восстановлено автоматически
(например, полное наименование развёрнуто из «ООО»), оно попадает
в `derived` и подсвечивается пользователю как требующее проверки.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import ENTREPRENEUR, CompanyData
from .morphology import normalize_person_name
from .readers import CardContent

# --------------------------------------------------------------- справочники
LEGAL_FORMS: list[tuple[str, str]] = [
    ("ПАО", "Публичное акционерное общество"),
    ("НАО", "Непубличное акционерное общество"),
    ("ЗАО", "Закрытое акционерное общество"),
    ("ОАО", "Открытое акционерное общество"),
    ("ООО", "Общество с ограниченной ответственностью"),
    ("АО", "Акционерное общество"),
    ("ИП", "Индивидуальный предприниматель"),
]
SHORT_BY_FULL = {full.lower(): short for short, full in LEGAL_FORMS}
FULL_BY_SHORT = {short: full for short, full in LEGAL_FORMS}

#: У предпринимателя после «ИП» стоит ФИО, а не название в кавычках.
#: Отсюда два отличия: кавычки не ставим и наименование не выдумываем.
ENTREPRENEUR_FORMS = {"ИП"}

POSITION_LABELS = {
    "генеральный директор", "директор", "исполнительный директор",
    "управляющий", "управляющий директор", "президент",
    "председатель правления", "начальник",
}

EMPTY_MARKERS = {"-", "--", "—", "–", "нет", "н/д", "нд", "не указано",
                 "отсутствует", "не заполнено", "нет данных", "…", "..."}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# (?<!\d) — «восьмёрка» телефона не должна стоять внутри более длинного числа:
# иначе в ИНН 781234567870 нашёлся бы «телефон» 81234567870.
PHONE_RE = re.compile(r"(?<!\d)(?:\+7|8)[\s\-()]*\d[\d\s\-()]{8,}\d")
DATE_RE = re.compile(r"\b(\d{2})[.\-/](\d{2})[.\-/](\d{4})\b")
FIO_RE = re.compile(
    r"\b([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?)\s+"
    r"([А-ЯЁ][а-яё]+)\s+"
    r"([А-ЯЁ][а-яё]+(?:ович|евич|ич|овна|евна|ична|инична))\b"
)
FIO_UPPER_RE = re.compile(r"\b([А-ЯЁ\-]{2,})\s+([А-ЯЁ]{2,})\s+([А-ЯЁ]{2,})\b")


@dataclass
class ParseResult:
    """Что удалось извлечь и на что стоит обратить внимание."""

    company: CompanyData
    derived: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------- утилиты
def _clean(value: str) -> str:
    text = re.sub(r"\s+", " ", (value or "")).strip(" \t\r\n;")
    if text.lower() in EMPTY_MARKERS:
        return ""
    return text


def _norm_label(label: str) -> str:
    """«р/сч.» → «р сч», «Эл. почта» → «эл почта» — чтобы сравнивать по смыслу."""
    text = (label or "").lower().replace("ё", "е")
    text = re.sub(r"[^а-яa-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _looks_like_phone(candidate: str) -> bool:
    """Похоже ли это на российский телефон, а не на карту или счёт?

    Российский номер — ровно 11 цифр (8 или 7, затем десятизначный
    номер). У карты 16 цифр, у расчётного счёта — 20, у ОГРН — 13 или 15.
    Все они могут начинаться с восьмёрки, поэтому одного «начинается на 8»
    мало: проверяем длину, чтобы номер карты предпринимателя не уехал
    в поле «Телефон».
    """
    digits = _digits(candidate)
    return len(digits) == 11 and digits[0] in "78"


LABEL_MAP: list[tuple[tuple[str, ...], str]] = [
    (("полное наименование", "полное фирменное наименование", "наименование организации",
      "полное название", "организация", "наименование юридического лица"), "full_name"),
    (("сокращенное наименование", "краткое наименование", "сокращенное название",
      "сокращенное фирменное наименование"), "short_name"),
    (("инн",), "inn"),
    (("кпп",), "kpp"),
    (("огрн", "огрнип"), "ogrn"),
    (("окпо",), "okpo"),
    (("окато", "октмо"), "okato"),
    (("дата регистрации", "дата гос регистрации", "дата государственной регистрации"),
     "registration_date"),
    (("юридический адрес", "адрес места нахождения", "место нахождения",
      "адрес регистрации", "юр адрес", "адрес"), "legal_address"),
    (("фактический адрес", "адрес фактический", "факт адрес",
      "адрес фактического местонахождения"), "actual_address"),
    (("почтовый адрес", "адрес для корреспонденции", "почт адрес"), "postal_address"),
    (("телефон", "тел", "тел факс", "контактный телефон", "телефоны"), "phone"),
    (("эл почта", "электронная почта", "email", "e mail", "почта", "мейл"), "email"),
    (("сайт", "웹", "web", "адрес сайта", "интернет сайт"), "website"),
    (("бик",), "bank_bik"),
    (("р сч", "р с", "расчетный счет", "расч счет", "счет"), "bank_account"),
    (("к сч", "к с", "корреспондентский счет", "корр счет"), "bank_corr_account"),
    (("банк", "наименование банка", "название банка"), "bank_name"),
]


def _field_for_label(label: str) -> str | None:
    norm = _norm_label(label)
    if not norm:
        return None
    for names, key in LABEL_MAP:
        if norm in names:
            return key
    for names, key in LABEL_MAP:
        for name in names:
            if len(name) > 3 and norm.startswith(name):
                return key
    return None


# --------------------------------------------------------------- наименование
def split_company_name(name: str) -> tuple[str, str, str]:
    """«ООО «Ромашка»» → ('ООО', 'Общество с ограниченной ответственностью', 'Ромашка').

    Возвращает (сокр. ОПФ, полная ОПФ, наименование без ОПФ и кавычек).
    Если ОПФ не распознана — первые два значения пустые.
    """
    text = _clean(name)
    if not text:
        return "", "", ""

    form_short, form_full = "", ""
    rest = text

    for full_lower, short in SHORT_BY_FULL.items():
        match = re.match(re.escape(full_lower), rest, flags=re.IGNORECASE)
        if match:
            form_short, form_full = short, FULL_BY_SHORT[short]
            rest = rest[match.end():].strip()
            break

    if not form_short:
        match = re.match(r"^(ПАО|НАО|ЗАО|ОАО|ООО|АО|ИП)\b\.?", rest, flags=re.IGNORECASE)
        if match:
            form_short = match.group(1).upper()
            form_full = FULL_BY_SHORT[form_short]
            rest = rest[match.end():].strip()

    # В карточках часто дублируют ОПФ: «Общество с ограниченной ответственностью ООО «X»».
    dup = re.match(r"^(ПАО|НАО|ЗАО|ОАО|ООО|АО|ИП)\b\.?", rest, flags=re.IGNORECASE)
    if dup and form_short:
        rest = rest[dup.end():].strip()

    bare = rest.strip().strip(",")
    bare = re.sub(r'^[«"\'`]+', "", bare)
    bare = re.sub(r'[»"\'`]+$', "", bare)
    return form_short, form_full, bare.strip()


def _compose_name(form: str, bare: str) -> str:
    if form and bare:
        # У предпринимателя после «ИП» идёт ФИО — кавычки там не ставятся.
        if form in ENTREPRENEUR_FORMS or form == FULL_BY_SHORT.get("ИП"):
            return f"{form} {bare}"
        return f"{form} «{bare}»"
    return bare or form


def _is_initials_of(short: str, full: str) -> bool:
    """«Иванов И.И.» — это сокращение от «Иванов Иван Иванович»?"""
    full_parts = (full or "").split()
    short_parts = (short or "").replace(".", " ").split()
    if len(full_parts) < 2 or len(short_parts) < 2:
        return False
    if full_parts[0].lower() != short_parts[0].lower():
        return False
    initials = [part[0].lower() for part in full_parts[1:]]
    given = [part[0].lower() for part in short_parts[1:] if part]
    return bool(given) and given == initials[:len(given)]


def looks_like_entrepreneur(*values: str) -> bool:
    """Похоже ли, что заявитель — индивидуальный предприниматель.

    Смотрим только на то, что реально написано в карточке: слова
    «индивидуальный предприниматель» или «ИП» в наименовании, длину ИНН
    (12 знаков вместо 10) и длину ОГРНИП (15 вместо 13). Ничего не
    домысливаем: если признаков нет, считаем заявителя юридическим лицом.
    """
    for value in values:
        text = (value or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered.startswith("индивидуальный предприниматель"):
            return True
        if re.match(r"^ип\b\.?\s", lowered) or lowered == "ип":
            return True
        digits = re.sub(r"\D", "", text)
        if digits and digits == re.sub(r"\s", "", text) and len(digits) in (12, 15):
            return True
    return False


# --------------------------------------------------------------- руководитель
def _extract_director(value: str, label: str = "") -> tuple[str, str, str]:
    """Возвращает (должность, ФИО, основание полномочий) из одной строки."""
    position, basis = "", ""
    text = _clean(value)

    label_norm = _norm_label(label)
    if label_norm in POSITION_LABELS:
        position = label.strip()

    # «... (на основании Устава)» или «действует на основании Устава»
    basis_match = re.search(
        r"на основании\s+([A-Za-zА-Яа-яЁё][^),.;]*)", text, flags=re.IGNORECASE)
    if basis_match:
        basis = basis_match.group(1).strip()
        text = text[: basis_match.start()] + text[basis_match.end():]
    text = re.sub(r"\(\s*\)", " ", text)
    text = re.sub(r"[()]", " ", text)

    # Должность может стоять внутри значения: «Генеральный директор Иванов И.И.»
    if not position:
        for candidate in sorted(POSITION_LABELS, key=len, reverse=True):
            pattern = re.compile(rf"\b{re.escape(candidate)}\b", flags=re.IGNORECASE)
            found = pattern.search(text)
            if found:
                position = found.group(0)
                text = text[: found.start()] + text[found.end():]
                break

    fio = _find_fio(text)
    return _normalize_position(position), fio, _normalize_basis(basis)


def _normalize_position(position: str) -> str:
    text = _clean(position).strip(":-— ")
    if not text:
        return ""
    return text[0].upper() + text[1:].lower() if text.isupper() else text[0].upper() + text[1:]


def _normalize_basis(basis: str) -> str:
    text = _clean(basis).strip(".,;: ")
    if not text:
        return ""
    lowered = text.lower()
    for stem, canonical in (("устав", "Устав"), ("доверенност", "Доверенность"),
                            ("решени", "Решение"), ("приказ", "Приказ"),
                            ("протокол", "Протокол"), ("договор", "Договор")):
        if lowered.startswith(stem):
            return canonical
    return text


def _find_fio(text: str) -> str:
    text = _clean(text).strip(":-— ")
    match = FIO_RE.search(text)
    if match:
        return " ".join(match.groups())
    match = FIO_UPPER_RE.search(text)
    if match:
        return normalize_person_name(" ".join(match.groups()))
    # Две-три подряд идущие кириллические «словоформы» без служебных слов.
    words = [w for w in re.split(r"[\s,]+", text) if re.fullmatch(r"[А-Яа-яЁё\-]{2,}", w)]
    stop = {"на", "основании", "устава", "устав", "действует", "действующий", "лице"}
    words = [w for w in words if w.lower() not in stop]
    if len(words) in (2, 3):
        return normalize_person_name(" ".join(words))
    return ""


# --------------------------------------------------------------- банк
def _split_account_and_bank(value: str) -> tuple[str, str]:
    """«№ 4070 2810 ... 1042 АО "АЛЬФА-БАНК"» → ('40702810...', 'АО "АЛЬФА-БАНК"')."""
    text = _clean(value)
    match = re.search(r"(?:\d[\s]?){20,}", text)
    if not match:
        return "", text
    account = _digits(match.group(0))[:20]
    tail = text[match.end():].strip(" ,;вв")
    tail = re.sub(r"^(в|в\s+)", "", tail).strip()
    return account, tail


# --------------------------------------------------------------- главный разбор
def parse_card(content: CardContent) -> ParseResult:
    """Разобрать содержимое карточки в реквизиты компании."""
    company = CompanyData()
    result = ParseResult(company)

    raw_values: dict[str, str] = {}

    def remember(key: str, value: str) -> None:
        value = _clean(value)
        if value and not raw_values.get(key):
            raw_values[key] = value

    # 1. Пары из таблиц.
    for label, value in content.pairs:
        key = _field_for_label(label)
        if key:
            remember(key, value)
        elif _norm_label(label) in POSITION_LABELS or "руководител" in _norm_label(label):
            position, fio, basis = _extract_director(value, label)
            remember("director_position", position)
            remember("director_full_name", fio)
            remember("director_basis", basis)

    # 2. Строки вида «Подпись: значение» / «Подпись — значение».
    for line in content.merged_text().splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^([^:|]{2,60}?)\s*[:|]\s*(.+)$", line)
        if match:
            label, value = match.group(1), match.group(2)
        else:
            match = re.match(r"^([А-Яа-яЁё /.]{3,40}?)\s{2,}(.+)$", line)
            if match:
                label, value = match.group(1), match.group(2)
            else:
                label, value = "", line

        if label:
            key = _field_for_label(label)
            if key:
                remember(key, value)
                continue
            label_norm = _norm_label(label)
            if label_norm in POSITION_LABELS or "руководител" in label_norm:
                position, fio, basis = _extract_director(value, label)
                remember("director_position", position)
                remember("director_full_name", fio)
                remember("director_basis", basis)
                continue

        # Строки без подписи: «ООО «Ромашка»», «Действует на основании Устава».
        if re.match(r"^(ПАО|НАО|ЗАО|ОАО|ООО|АО)\s*[«\"']", line, flags=re.IGNORECASE):
            remember("short_name", line)
        elif re.match(r"^(Общество|Акционерное|Публичное|Непубличное|Закрытое|Открытое)",
                      line, flags=re.IGNORECASE):
            remember("full_name", line)
        elif re.search(r"действу\w*\s+на основании", line, flags=re.IGNORECASE):
            basis_match = re.search(r"на основании\s+(.+)$", line, flags=re.IGNORECASE)
            if basis_match:
                remember("director_basis", _normalize_basis(basis_match.group(1)))

    # 3. Резервный поиск по всему тексту.
    text = content.merged_text()
    if not raw_values.get("inn"):
        match = re.search(r"\bИНН\D{0,4}(\d[\d\s]{8,14}\d)", text, flags=re.IGNORECASE)
        if match:
            remember("inn", match.group(1))
    if not raw_values.get("kpp"):
        match = re.search(r"\bКПП\D{0,4}(\d[\d\s]{7,11}\d)", text, flags=re.IGNORECASE)
        if match:
            remember("kpp", match.group(1))
    if not raw_values.get("ogrn"):
        match = re.search(r"\bОГРН(?:ИП)?\D{0,4}(\d[\d\s]{11,18}\d)", text, flags=re.IGNORECASE)
        if match:
            remember("ogrn", match.group(1))
    if not raw_values.get("email"):
        match = EMAIL_RE.search(text)
        if match:
            remember("email", match.group(0))
    if not raw_values.get("phone"):
        # Ищем построчно и проверяем длину: номер карты или счёта, даже если
        # он начинается с 8, за телефон не примем (у телефона ровно 11 цифр).
        for line in text.splitlines():
            match = PHONE_RE.search(line)
            if match and _looks_like_phone(match.group(0)):
                remember("phone", match.group(0))
                break
    if not raw_values.get("director_full_name"):
        for line in text.splitlines():
            if re.search(r"директор|руководител|президент|управляющ", line, flags=re.IGNORECASE):
                position, fio, basis = _extract_director(line)
                if fio:
                    remember("director_position", position)
                    remember("director_full_name", fio)
                    remember("director_basis", basis)
                    break

    # ---------------------------------------------------------- раскладка
    for key in ("inn", "kpp", "ogrn", "okpo", "okato", "bank_bik"):
        if raw_values.get(key):
            company.set(key, _digits(raw_values[key]))

    for key in ("legal_address", "actual_address", "postal_address",
                "phone", "email", "website", "bank_name"):
        if raw_values.get(key):
            company.set(key, raw_values[key])

    if raw_values.get("email"):
        found = EMAIL_RE.search(raw_values["email"])
        company.set("email", found.group(0) if found else raw_values["email"])

    if raw_values.get("registration_date"):
        match = DATE_RE.search(raw_values["registration_date"])
        if match:
            company.set("registration_date", ".".join(match.groups()))

    for src, dst in (("bank_account", "bank_account"), ("bank_corr_account", "bank_corr_account")):
        if raw_values.get(src):
            account, bank = _split_account_and_bank(raw_values[src])
            company.set(dst, account or _digits(raw_values[src]))
            if bank and not company.bank_name and dst == "bank_account":
                company.set("bank_name", bank)

    company.set("director_position", raw_values.get("director_position", ""))
    company.set("director_full_name",
                normalize_person_name(raw_values.get("director_full_name", "")))
    company.set("director_basis", raw_values.get("director_basis", ""))

    # ---------------------------------------------------------- наименования
    full_raw = raw_values.get("full_name", "")
    short_raw = raw_values.get("short_name", "")

    full_form_short, full_form_full, full_bare = split_company_name(full_raw)
    short_form_short, _, short_bare = split_company_name(short_raw)

    if full_raw:
        company.set("full_name", _compose_name(full_form_full or full_form_short, full_bare)
                    if full_bare else full_raw)
    if short_raw:
        company.set("short_name", _compose_name(short_form_short, short_bare)
                    if short_bare else short_raw)

    # Восстановление недостающего наименования — только из формы, с пометкой.
    if not company.full_name and company.short_name and short_form_short:
        company.set("full_name",
                    _compose_name(FULL_BY_SHORT[short_form_short], short_bare))
        result.derived["full_name"] = (
            "Развёрнуто из сокращённого наименования. Сверьте с Уставом: "
            "в полном наименовании название пишется так же, как в сокращённом, "
            "далеко не всегда."
        )
    if not company.short_name and company.full_name and full_form_short:
        company.set("short_name", _compose_name(full_form_short, full_bare))
        result.derived["short_name"] = (
            "Свёрнуто из полного наименования. Сверьте с Уставом: сокращённое "
            "название часто отличается (например, «ТеплоЭнергоСтрой» → «ТЭС»)."
        )

    if company.full_name and company.short_name:
        _, _, fb = split_company_name(company.full_name)
        _, _, sb = split_company_name(company.short_name)
        # У предпринимателя полное — это ФИО, а сокращённое — фамилия
        # с инициалами. Это не расхождение, а норма, и сообщать не о чем.
        same_person = _is_initials_of(sb, fb)
        if fb and sb and fb.lower() != sb.lower() and not same_person:
            result.notes.append(
                f"В полном и сокращённом наименовании разные названия: "
                f"«{fb}» и «{sb}». Так бывает, но проверьте по Уставу."
            )

    # ------------------------------------------------- юрлицо или предприниматель
    # Определяем по тому, что реально написано в карточке. Ничего не
    # додумываем: тип всегда виден в окне, и его можно переключить.
    if looks_like_entrepreneur(company.full_name, company.short_name,
                               company.inn, company.ogrn):
        company.applicant_kind = ENTREPRENEUR
        result.notes.append(
            "Заявитель распознан как индивидуальный предприниматель "
            "(по наименованию или по длине ИНН и ОГРНИП). Если это не так, "
            "переключите тип заявителя в верхней части окна."
        )

    result.company = company
    return result


def parse_text(text: str) -> ParseResult:
    """Разобрать реквизиты из вставленного текста."""
    from .readers import read_pasted_text
    return parse_card(read_pasted_text(text))
