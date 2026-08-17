# -*- coding: utf-8 -*-
"""Проверка реквизитов.

Правило: программа НИКОГДА не исправляет значение сама. Она только
сообщает, что не так, понятным русским языком.

Единственное, что делается автоматически, — очистка от «мусорных»
пробелов и неразрывных пробелов внутри цифровых идентификаторов;
об этом пользователю сообщается отдельным предупреждением.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


@dataclass
class Issue:
    """Замечание к значению поля."""

    field: str
    text: str
    severity: str = "error"  # error | warning

    @property
    def is_error(self) -> bool:
        return self.severity == "error"


# ---------------------------------------------------------------- цифры
def digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _looks_dirty(value: str) -> bool:
    """Есть ли внутри значения пробелы/разделители, которых быть не должно."""
    return bool(re.search(r"[\s \-]", (value or "").strip()))


def inn_checksum_ok(inn: str) -> bool | None:
    """Контрольное число ИНН. None — если длина не 10 и не 12."""
    d = digits_only(inn)
    if len(d) == 10:
        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        control = sum(int(d[i]) * weights[i] for i in range(9)) % 11 % 10
        return control == int(d[9])
    if len(d) == 12:
        w1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        w2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        c1 = sum(int(d[i]) * w1[i] for i in range(10)) % 11 % 10
        c2 = sum(int(d[i]) * w2[i] for i in range(11)) % 11 % 10
        return c1 == int(d[10]) and c2 == int(d[11])
    return None


def ogrn_checksum_ok(ogrn: str) -> bool | None:
    """Контрольное число ОГРН (13 знаков) и ОГРНИП (15 знаков)."""
    d = digits_only(ogrn)
    if len(d) == 13:
        return int(d[:12]) % 11 % 10 == int(d[12])
    if len(d) == 15:
        return int(d[:14]) % 13 % 10 == int(d[14])
    return None


# ---------------------------------------------------------------- поля
def validate_inn(value: str) -> list[Issue]:
    raw = (value or "").strip()
    if not raw:
        return []
    d = digits_only(raw)
    issues: list[Issue] = []
    if _looks_dirty(raw):
        issues.append(Issue("inn", f"ИНН «{raw}» содержит пробелы или дефисы — "
                                   f"в документ будет подставлено «{d}». Проверьте значение.",
                            "warning"))
    if not d:
        return [Issue("inn", f"ИНН «{raw}» не содержит цифр. Проверьте значение.")]
    if len(d) == 12:
        issues.append(Issue("inn", f"Введён ИНН {d} — это 12 цифр, такой ИНН бывает у "
                                   f"индивидуального предпринимателя или физлица. "
                                   f"Шаблоны рассчитаны на юридическое лицо (10 цифр). "
                                   f"Проверьте значение."))
        return issues
    if len(d) != 10:
        issues.append(Issue("inn", f"Введён ИНН {d}. Для юридического лица ожидается "
                                   f"10 цифр, введено {len(d)}. Проверьте значение."))
        return issues
    if inn_checksum_ok(d) is False:
        issues.append(Issue("inn", f"ИНН {d} не проходит проверку контрольного числа. "
                                   f"Скорее всего, в одной из цифр опечатка. "
                                   f"Проверьте значение."))
    return issues


def validate_kpp(value: str) -> list[Issue]:
    raw = (value or "").strip()
    if not raw:
        return []
    d = digits_only(raw)
    issues: list[Issue] = []
    if _looks_dirty(raw):
        issues.append(Issue("kpp", f"КПП «{raw}» содержит лишние символы — "
                                   f"будет использовано «{d}».", "warning"))
    if len(d) != 9:
        issues.append(Issue("kpp", f"Введён КПП {d}. Ожидается 9 цифр, введено {len(d)}. "
                                   f"Проверьте значение."))
    return issues


def validate_ogrn(value: str) -> list[Issue]:
    raw = (value or "").strip()
    if not raw:
        return []
    d = digits_only(raw)
    issues: list[Issue] = []
    if _looks_dirty(raw):
        issues.append(Issue("ogrn", f"ОГРН «{raw}» содержит пробелы или дефисы — "
                                    f"в документ будет подставлено «{d}».", "warning"))
    if not d:
        return [Issue("ogrn", f"ОГРН «{raw}» не содержит цифр. Проверьте значение.")]
    if len(d) == 15:
        issues.append(Issue("ogrn", f"Введён ОГРНИП {d} (15 цифр) — это номер "
                                    f"индивидуального предпринимателя. Шаблоны рассчитаны "
                                    f"на юридическое лицо (ОГРН, 13 цифр). Проверьте значение."))
        return issues
    if len(d) != 13:
        issues.append(Issue("ogrn", f"Введён ОГРН {d}. Ожидается 13 цифр, введено {len(d)}. "
                                    f"Проверьте значение."))
        return issues
    if ogrn_checksum_ok(d) is False:
        issues.append(Issue("ogrn", f"ОГРН {d} не проходит проверку контрольного числа. "
                                    f"Скорее всего, в одной из цифр опечатка. "
                                    f"Проверьте значение."))
    return issues


def validate_email(value: str) -> list[Issue]:
    raw = (value or "").strip()
    if not raw:
        return []
    if " " in raw:
        return [Issue("email", f"Адрес электронной почты «{raw}» содержит пробел. "
                               f"Проверьте значение.")]
    if not EMAIL_RE.match(raw):
        return [Issue("email", f"Адрес электронной почты «{raw}» выглядит некорректно "
                               f"(ожидается вид name@domain.ru). Проверьте значение.")]
    return []


def validate_phone(value: str) -> list[Issue]:
    raw = (value or "").strip()
    if not raw:
        return []
    d = digits_only(raw)
    if len(d) < 10:
        return [Issue("phone", f"Телефон «{raw}» содержит только {len(d)} цифр. "
                               f"Ожидается не менее 10. Проверьте значение.")]
    if len(d) > 15:
        return [Issue("phone", f"Телефон «{raw}» содержит {len(d)} цифр — это больше, "
                               f"чем бывает у одного номера. Проверьте значение.")]
    return []


def validate_bik(value: str) -> list[Issue]:
    raw = (value or "").strip()
    if not raw:
        return []
    d = digits_only(raw)
    if len(d) != 9:
        return [Issue("bank_bik", f"БИК {d}: ожидается 9 цифр, введено {len(d)}. "
                                  f"Проверьте значение.", "warning")]
    return []


def validate_account(value: str, field_name: str, label: str) -> list[Issue]:
    raw = (value or "").strip()
    if not raw:
        return []
    d = digits_only(raw)
    if len(d) != 20:
        return [Issue(field_name, f"{label}: ожидается 20 цифр, введено {len(d)}. "
                                  f"Проверьте значение.", "warning")]
    return []


def validate_company_name(value: str, field_name: str, label: str) -> list[Issue]:
    raw = (value or "").strip()
    if not raw:
        return []
    if "«" in raw and "»" not in raw:
        return [Issue(field_name, f"{label}: открывающая кавычка « есть, а закрывающей » нет. "
                                  f"Проверьте значение.")]
    return []


def validate_date(value: str, field_name: str, label: str) -> list[Issue]:
    raw = (value or "").strip()
    if not raw:
        return []
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", raw):
        return [Issue(field_name, f"{label}: ожидается дата в виде ДД.ММ.ГГГГ, "
                                  f"введено «{raw}». Проверьте значение.")]
    day, month, year = (int(x) for x in raw.split("."))
    if not (1 <= month <= 12) or not (1 <= day <= 31) or not (1900 <= year <= 2100):
        return [Issue(field_name, f"{label}: дата «{raw}» не существует. Проверьте значение.")]
    return []


# ---------------------------------------------------------------- всё сразу
def validate_company(company) -> list[Issue]:
    """Технические проверки всех заполненных полей компании."""
    issues: list[Issue] = []
    issues += validate_company_name(company.full_name, "full_name", "Полное наименование")
    issues += validate_company_name(company.short_name, "short_name", "Сокращённое наименование")
    issues += validate_inn(company.inn)
    issues += validate_kpp(company.kpp)
    issues += validate_ogrn(company.ogrn)
    issues += validate_email(company.email)
    issues += validate_phone(company.phone)
    issues += validate_bik(company.bank_bik)
    issues += validate_account(company.bank_account, "bank_account", "Расчётный счёт")
    issues += validate_account(company.bank_corr_account, "bank_corr_account",
                               "Корреспондентский счёт")
    issues += validate_date(company.registration_date, "registration_date", "Дата регистрации")
    issues += validate_date(company.doc_date, "doc_date", "Дата документов")
    return issues
