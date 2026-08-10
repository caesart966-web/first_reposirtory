"""Валидация ИНН и ОГРН/ОГРНИП по официальным контрольным суммам ФНС."""
from __future__ import annotations

import re
from typing import Optional

_DIGITS_RE = re.compile(r"\D+")

# Коэффициенты контрольных сумм ИНН
_INN10_COEF = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_COEF_11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN12_COEF_12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


def clean_digits(value: str) -> str:
    """Оставить только цифры (убирает пробелы, дефисы, «ИНН:» и т.п.)."""
    return _DIGITS_RE.sub("", value or "")


def _checksum(digits: str, coefficients: tuple[int, ...]) -> int:
    return sum(int(d) * c for d, c in zip(digits, coefficients)) % 11 % 10


def validate_inn(value: str) -> tuple[bool, str]:
    """Проверка ИНН (10 цифр — юрлицо, 12 — физлицо/ИП).

    Возвращает (валиден, причина отбраковки или тип: «юрлицо»/«ИП или физлицо»).
    """
    digits = clean_digits(value)
    if not digits:
        return False, "пустой ИНН"
    if len(digits) == 10:
        if digits == "0" * 10:
            return False, "ИНН из одних нулей"
        if _checksum(digits[:9], _INN10_COEF) != int(digits[9]):
            return False, "неверная контрольная сумма ИНН (10 знаков)"
        return True, "юрлицо"
    if len(digits) == 12:
        if digits == "0" * 12:
            return False, "ИНН из одних нулей"
        if _checksum(digits[:10], _INN12_COEF_11) != int(digits[10]):
            return False, "неверная контрольная сумма ИНН (11-й знак)"
        if _checksum(digits[:11], _INN12_COEF_12) != int(digits[11]):
            return False, "неверная контрольная сумма ИНН (12-й знак)"
        return True, "ИП или физлицо"
    return False, f"ИНН должен содержать 10 или 12 цифр, получено {len(digits)}"


def is_valid_inn(value: str) -> bool:
    return validate_inn(value)[0]


def validate_ogrn(value: str) -> tuple[bool, str]:
    """Проверка ОГРН (13 цифр) и ОГРНИП (15 цифр)."""
    digits = clean_digits(value)
    if not digits:
        return False, "пустой ОГРН"
    if len(digits) == 13:
        control = int(digits[:12]) % 11 % 10
        if control != int(digits[12]):
            return False, "неверная контрольная сумма ОГРН"
        return True, "ОГРН юрлица"
    if len(digits) == 15:
        control = int(digits[:14]) % 13 % 10
        if control != int(digits[14]):
            return False, "неверная контрольная сумма ОГРНИП"
        return True, "ОГРНИП"
    return False, f"ОГРН должен содержать 13 или 15 цифр, получено {len(digits)}"


def is_valid_ogrn(value: str) -> bool:
    return validate_ogrn(value)[0]


def looks_like_inn(value: str) -> bool:
    """Похоже ли значение на ИНН (для автоопределения колонок)."""
    digits = clean_digits(str(value))
    return len(digits) in (10, 12) and is_valid_inn(digits)


def looks_like_ogrn(value: str) -> bool:
    digits = clean_digits(str(value))
    return len(digits) in (13, 15) and is_valid_ogrn(digits)


def extract_inn(value: str) -> Optional[str]:
    """Достать валидный ИНН из строки, если он там есть."""
    digits = clean_digits(str(value))
    if len(digits) in (10, 12) and is_valid_inn(digits):
        return digits
    return None
