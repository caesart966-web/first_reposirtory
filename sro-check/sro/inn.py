"""Приведение ИНН к нормальному виду и проверка контрольной суммы.

Зачем это нужно. Excel часто хранит ИНН как ЧИСЛО, а не как текст.
Из-за этого:
  * ИНН, начинающийся с нуля (Адыгея 01..., Башкортостан 02...), теряет
    первый ноль и превращается в 9 знаков вместо 10;
  * значение может прийти как 7702521529.0 (число с плавающей точкой).
Обе проблемы здесь чинятся.
"""

from __future__ import annotations

import re

_NON_DIGIT = re.compile(r"\D")

# Коэффициенты для контрольных разрядов (Приказ ФНС о порядке присвоения ИНН)
_W10 = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_W11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_W12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)


def normalize_inn(value) -> str:
    """Превратить значение ячейки в строку ИНН из 10 или 12 цифр.

    Возвращает пустую строку, если из значения не получается вытащить ИНН.
    """
    if value is None:
        return ""

    if isinstance(value, float):
        # 7702521529.0 -> "7702521529"; float64 точно представляет любое
        # 12-значное целое, так что потери разрядов здесь нет.
        if value.is_integer():
            text = str(int(value))
        else:
            text = repr(value)
    elif isinstance(value, int):
        text = str(value)
    else:
        text = str(value)

    digits = _NON_DIGIT.sub("", text)
    if not digits:
        return ""

    # Восстанавливаем ведущий ноль, съеденный Excel-ом.
    if len(digits) == 9:
        digits = "0" + digits
    elif len(digits) == 11:
        digits = "0" + digits

    return digits


def is_valid_inn(inn: str) -> bool:
    """Проверить длину и контрольную сумму ИНН."""
    if not inn or not inn.isdigit():
        return False

    def control(digits: str, weights: tuple[int, ...]) -> int:
        return sum(int(d) * w for d, w in zip(digits, weights)) % 11 % 10

    if len(inn) == 10:
        return control(inn[:9], _W10) == int(inn[9])
    if len(inn) == 12:
        return control(inn[:10], _W11) == int(inn[10]) and control(inn[:11], _W12) == int(inn[11])
    return False


def describe_problem(raw_value, inn: str) -> str:
    """Человекочитаемая причина, почему ИНН нельзя проверить."""
    if not inn:
        if raw_value is None or str(raw_value).strip() == "":
            return "ИНН не указан"
        return f"не удалось разобрать ИНН из значения «{raw_value}»"
    if len(inn) not in (10, 12):
        return f"ИНН «{inn}» неверной длины ({len(inn)} знаков вместо 10 или 12)"
    if not is_valid_inn(inn):
        return f"ИНН «{inn}» не проходит проверку контрольной суммы"
    return ""
