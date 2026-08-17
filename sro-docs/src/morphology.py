# -*- coding: utf-8 -*-
"""Русская морфология: родительный падеж ФИО и должностей.

Принцип: правила применяются только там, где они надёжны. Если уверенности
нет — функция возвращает `confident=False`, и программа спрашивает человека,
а не подставляет догадку в юридический документ.

Полностью локально, без внешних сервисов и словарей.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VOWELS = "аеёиоуыэюя"

# Фамилии, которые в русском языке не склоняются вовсе.
INDECLINABLE_SUFFIXES = (
    "ко", "енко", "ько", "аго", "яго", "ово", "ых", "их",
    "е", "и", "о", "у", "ю", "ы", "э",
)

# Окончания мужских фамилий с «беглой» гласной: правило здесь ненадёжно,
# поэтому программа не склоняет их сама, а спрашивает пользователя.
UNRELIABLE_SURNAME_SUFFIXES = ("ей", "ец", "ок", "ёк", "ёл", "ень", "оть", "аец")


@dataclass
class Inflected:
    """Результат склонения."""

    value: str
    confident: bool
    reason: str = ""

    def __str__(self) -> str:  # удобно в f-строках
        return self.value


# ---------------------------------------------------------------- пол
def detect_gender(full_name: str) -> str:
    """Определяет пол по отчеству. Возвращает 'm', 'f' или '?'.

    Отчество — самый надёжный признак в русском языке, поэтому пол по имени
    или фамилии мы принципиально не угадываем.
    """
    parts = _split(full_name)
    if len(parts) < 3:
        return "?"
    patronymic = parts[2].lower()
    if patronymic.endswith(("овна", "евна", "ична", "инична", "ична")):
        return "f"
    if patronymic.endswith(("ович", "евич", "ич", "ыч")):
        return "m"
    return "?"


def _split(full_name: str) -> list[str]:
    return [p for p in re.split(r"\s+", (full_name or "").strip()) if p]


# ---------------------------------------------------------------- отчество
def _patronymic_genitive(word: str, gender: str) -> Inflected:
    low = word.lower()
    if gender == "m":
        if low.endswith(("ович", "евич", "ич", "ыч")):
            return Inflected(word + "а", True)
    if gender == "f":
        for tail in ("овна", "евна", "инична", "ична"):
            if low.endswith(tail):
                return Inflected(word[: -len(tail)] + tail[:-1] + "ы", True)
    return Inflected(word, False, "неизвестная форма отчества")


# ---------------------------------------------------------------- имя
MALE_NAME_EXCEPTIONS = {"лев": "Льва", "павел": "Павла", "пётр": "Петра", "петр": "Петра"}


def _first_name_genitive(word: str, gender: str) -> Inflected:
    low = word.lower()
    if gender == "m":
        if low in MALE_NAME_EXCEPTIONS:
            return Inflected(_match_case(word, MALE_NAME_EXCEPTIONS[low]), True)
        if low.endswith("й"):                       # Андрей → Андрея
            return Inflected(word[:-1] + "я", True)
        if low.endswith("ь"):                       # Игорь → Игоря
            return Inflected(word[:-1] + "я", True)
        if low.endswith("я"):                       # Илья → Ильи
            return Inflected(word[:-1] + "и", True)
        if low.endswith("а"):                       # Никита → Никиты
            return Inflected(word[:-1] + ("и" if low[-2] in "гкхжчшщ" else "ы"), True)
        if low[-1] not in VOWELS:                   # Иван → Ивана
            return Inflected(word + "а", True)
        return Inflected(word, False, "нестандартное мужское имя")
    if gender == "f":
        if low.endswith("ия"):                      # Мария → Марии
            return Inflected(word[:-1] + "и", True)
        if low.endswith("я"):                       # Ольга-подобные на -я → -и
            return Inflected(word[:-1] + "и", True)
        if low.endswith("а"):                       # Анна → Анны, Ольга → Ольги
            return Inflected(word[:-1] + ("и" if low[-2] in "гкхжчшщ" else "ы"), True)
        if low == "любовь":
            return Inflected(_match_case(word, "Любови"), True)
        return Inflected(word, False, "нестандартное женское имя")
    return Inflected(word, False, "пол не определён")


# ---------------------------------------------------------------- фамилия
def _surname_genitive(word: str, gender: str) -> Inflected:
    low = word.lower()

    # Составные фамилии через дефис склоняются по частям.
    if "-" in word:
        parts = word.split("-")
        results = [_surname_genitive(p, gender) for p in parts]
        return Inflected(
            "-".join(r.value for r in results),
            all(r.confident for r in results),
            "; ".join(r.reason for r in results if r.reason),
        )

    if low.endswith(INDECLINABLE_SUFFIXES) and not low.endswith(("ово", "аго", "яго")):
        # -ко, -ых, -их, а также иноязычные на гласную: не склоняются
        if low.endswith(("ко", "ых", "их")) or low[-1] in "еиоуюыэ":
            return Inflected(word, True, "несклоняемая фамилия")

    if gender == "m":
        if low.endswith(("ов", "ев", "ёв", "ин", "ын")):        # Иванов → Иванова
            return Inflected(word + "а", True)
        if low.endswith(UNRELIABLE_SURNAME_SUFFIXES):
            # Беглая гласная: Соловей → Соловья, но Кочубей → Кочубея;
            # Кравец → Кравца, но Швец → Швеца. Правилом не берётся — спросим.
            return Inflected(word, False,
                             "в такой фамилии гласная может выпадать "
                             "(Соловей → Соловья, но Кочубей → Кочубея)")
        if low.endswith(("ский", "цкий", "ый", "ий")):          # Донской-тип → -ого
            return Inflected(word[:-2] + "ого", True)
        if low.endswith("ой"):                                  # Толстой → Толстого
            return Inflected(word[:-2] + "ого", True)
        if low.endswith("ь"):                                   # Врубель → Врубеля
            return Inflected(word[:-1] + "я", True)
        if low.endswith("й"):
            return Inflected(word[:-1] + "я", True)
        if low.endswith("а"):
            return Inflected(word[:-1] + ("и" if low[-2] in "гкхжчшщ" else "ы"), True)
        if low.endswith("я"):
            return Inflected(word[:-1] + "и", True)
        if low[-1] not in VOWELS:                               # Кузнец → Кузнеца
            return Inflected(word + "а", True)
        return Inflected(word, False, "нестандартная мужская фамилия")

    if gender == "f":
        if low.endswith(("ова", "ева", "ёва", "ина", "ына")):   # Иванова → Ивановой
            return Inflected(word[:-1] + "ой", True)
        if low.endswith(("ская", "цкая", "ая")):                # Донская → Донской
            return Inflected(word[:-2] + "ой", True)
        if low.endswith("а"):
            return Inflected(word[:-1] + ("и" if low[-2] in "гкхжчшщ" else "ы"), True)
        if low.endswith("я"):
            return Inflected(word[:-1] + "и", True)
        # Женские фамилии на согласный и на -ь не склоняются: Гринберг, Пресняк
        return Inflected(word, True, "женская фамилия на согласный не склоняется")

    return Inflected(word, False, "пол не определён")


# ---------------------------------------------------------------- ФИО целиком
def full_name_genitive(full_name: str) -> Inflected:
    """«Хомутов Роман Сергеевич» → «Хомутова Романа Сергеевича»."""
    parts = _split(full_name)
    if not parts:
        return Inflected("", False, "ФИО не указано")
    if len(parts) < 2:
        return Inflected(full_name, False, "ожидались минимум фамилия и имя")
    if len(parts) > 3:
        return Inflected(full_name, False, "более трёх слов в ФИО — проверьте вручную")

    gender = detect_gender(full_name)
    if gender == "?":
        return Inflected(full_name, False, "не удалось определить пол по отчеству")

    surname = _surname_genitive(parts[0], gender)
    first = _first_name_genitive(parts[1], gender)
    pieces = [surname, first]
    if len(parts) == 3:
        pieces.append(_patronymic_genitive(parts[2], gender))

    reasons = [p.reason for p in pieces if p.reason and not p.confident]
    return Inflected(
        " ".join(p.value for p in pieces),
        all(p.confident for p in pieces),
        "; ".join(reasons),
    )


def short_name(full_name: str) -> Inflected:
    """«Хомутов Роман Сергеевич» → «Хомутов Р.С.»"""
    parts = _split(full_name)
    if not parts:
        return Inflected("", False, "ФИО не указано")
    if len(parts) == 1:
        return Inflected(parts[0], False, "в ФИО только одно слово")
    initials = "".join(f"{p[0].upper()}." for p in parts[1:])
    return Inflected(f"{parts[0]} {initials}", True)


# ---------------------------------------------------------------- должность
# Готовые формы для должностей, которые реально встречаются в СРО-документах.
POSITION_GENITIVE = {
    "генеральный директор": "Генерального директора",
    "директор": "Директора",
    "исполнительный директор": "Исполнительного директора",
    "управляющий": "Управляющего",
    "управляющий директор": "Управляющего директора",
    "президент": "Президента",
    "председатель правления": "Председателя правления",
    "руководитель": "Руководителя",
    "начальник": "Начальника",
    "индивидуальный предприниматель": "Индивидуального предпринимателя",
    "единоличный исполнительный орган": "Единоличного исполнительного органа",
}

# Основания полномочий.
BASIS_GENITIVE = {
    "устав": "Устава",
    "устава": "Устава",
    "доверенность": "Доверенности",
    "доверенности": "Доверенности",
    "решение": "Решения",
    "решения": "Решения",
    "приказ": "Приказа",
    "приказа": "Приказа",
    "протокол": "Протокола",
    "протокола": "Протокола",
    "договор": "Договора",
    "договора": "Договора",
}


def position_genitive(position: str) -> Inflected:
    """«Генеральный директор» → «Генерального директора»."""
    text = (position or "").strip()
    if not text:
        return Inflected("", False, "должность не указана")
    known = POSITION_GENITIVE.get(text.lower())
    if known:
        return Inflected(_match_case(text, known), True)
    return Inflected(text, False, "неизвестная должность — проверьте родительный падеж")


def basis_genitive(basis: str) -> Inflected:
    """«Устав» → «Устава». Умеет отрезать хвост вида «Устава (ред. 2024)»."""
    text = (basis or "").strip().strip(".")
    if not text:
        return Inflected("", False, "основание полномочий не указано")
    head = text.split()[0].lower().strip(",")
    known = BASIS_GENITIVE.get(head)
    if known:
        tail = text[len(text.split()[0]):].strip()
        return Inflected((known + (" " + tail if tail else "")).strip(), True)
    return Inflected(text, False, "неизвестное основание — проверьте родительный падеж")


# ---------------------------------------------------------------- утилиты
def _match_case(source: str, replacement: str) -> str:
    """Сохраняет регистр исходной строки (ВЕРХНИЙ / Первая буква)."""
    if source.isupper():
        return replacement.upper()
    return replacement


def normalize_person_name(raw: str) -> str:
    """«ИВАНОВ ИВАН ИВАНОВИЧ» → «Иванов Иван Иванович».

    Смешанный регистр не трогаем: пользователь мог намеренно написать
    «де Голль» или «МакДональд».
    """
    text = re.sub(r"\s+", " ", (raw or "").strip())
    if not text:
        return ""
    letters = [c for c in text if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return " ".join(
            "-".join(part.capitalize() for part in word.split("-"))
            for word in text.split(" ")
        )
    return text


MONTHS_GENITIVE = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]
