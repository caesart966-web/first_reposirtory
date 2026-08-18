# -*- coding: utf-8 -*-
"""Понятное объяснение, если программа не смогла запуститься.

Вызывается из START.bat, когда окно программы завершилось с ошибкой.
Смотрит в лог и подсказывает, что делать, обычным русским языком.
"""

from __future__ import print_function

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "logs", "app.log")

HINTS = [
    ("tkinter", [
        "В установленном Python не хватает части, отвечающей за окна (tkinter).",
        "Переустановите Python с сайта python.org, выбрав обычную установку",
        "(Install Now) - в ней tkinter входит по умолчанию.",
    ]),
    ("Permission denied", [
        "Windows не дал изменить файл. Скорее всего, готовый документ",
        "открыт в Word. Закройте его и попробуйте снова.",
    ]),
    ("No space left", [
        "На диске закончилось свободное место.",
    ]),
    ("не найден шаблон", [
        "Не хватает файлов шаблонов в папке templates.",
        "Распакуйте архив программы заново, целиком.",
    ]),
]


def tail(path, count=40):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.readlines()[-count:]
    except OSError:
        return []


def main():
    print()
    print("=" * 62)
    print("  Программа завершилась с ошибкой")
    print("=" * 62)
    print()

    lines = tail(LOG)
    text = "".join(lines)

    for marker, advice in HINTS:
        if marker.lower() in text.lower():
            for line in advice:
                print("  " + line)
            print()
            break
    else:
        if lines:
            print("  Последние записи из журнала:")
            print()
            for line in lines[-12:]:
                print("    " + line.rstrip())
            print()
        print("  Что можно сделать:")
        print("    1. Закройте документы Word, если они открыты.")
        print("    2. Запустите START.bat ещё раз.")
        print("    3. Если не помогло - удалите папку .venv и запустите снова.")
        print()

    print("  Полный журнал: " + LOG)
    print("  Персональных данных в нём нет.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
