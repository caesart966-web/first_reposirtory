# -*- coding: utf-8 -*-
"""Диагностика: почему не открывается окно программы.

Запускается двойным щелчком по DIAGNOSTIKA.bat. Ничего не меняет в системе,
только смотрит и пишет понятный отчёт:

  * какая версия Python и что за система;
  * стоят ли нужные библиотеки;
  * загружаются ли настройки СРО;
  * СТАРАЯ у пользователя версия программы или новая (с исправлением окна);
  * последние строки журнала — как далеко дошёл прошлый запуск.

Отчёт сохраняется в logs/DIAGNOSTIKA.txt, открывается в Блокноте, а затем
скрипт пробует показать маленькое тестовое окно — чтобы проверить, работает
ли графика вообще.
"""

from __future__ import print_function

import io
import os
import platform
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS = os.path.join(ROOT, "logs")
REPORT = os.path.join(LOGS, "DIAGNOSTIKA.txt")

_lines = []


def add(text=""):
    _lines.append(text)
    print(text)
    try:
        sys.stdout.flush()
    except Exception:  # noqa: BLE001
        pass


def _now():
    # Без сторонних библиотек: локальное время в понятном виде.
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _has_fix():
    """Есть ли в этой копии вчерашнее исправление окна выбора СРО."""
    gui = os.path.join(ROOT, "src", "gui.py")
    try:
        with io.open(gui, encoding="utf-8", errors="replace") as handle:
            return "_present_modal" in handle.read()
    except OSError:
        return None


def collect():
    add("=" * 64)
    add("  ДИАГНОСТИКА  «Документы для вступления в СРО»")
    add("=" * 64)
    add("Время:   " + _now())
    add("Python:  " + sys.version.split()[0])
    add("         " + sys.executable)
    add("Система: " + platform.platform())
    add("Папка:   " + ROOT)
    add("")

    fix = _has_fix()
    add("-" * 64)
    if fix is True:
        add("  ВЕРСИЯ ПРОГРАММЫ: новая (исправление окна на месте).")
    elif fix is False:
        add("  ВЕРСИЯ ПРОГРАММЫ: СТАРАЯ — без исправления окна.")
        add("  Скачайте программу заново: окно не открывалось именно из-за")
        add("  этого. После обновления запустите START.bat ещё раз.")
    else:
        add("  ВЕРСИЯ ПРОГРАММЫ: не удалось определить (нет src/gui.py?).")
    add("-" * 64)
    add("")

    add("Библиотеки:")
    modules = [
        ("tkinter", "окно программы (без него ничего не покажется)"),
        ("docx", "чтение и запись Word"),
        ("lxml", "работа с документом"),
        ("openpyxl", "чтение Excel"),
        ("PIL", "картинки и распознавание"),
        ("fitz", "чтение PDF"),
        ("tkinterdnd2", "перетаскивание файла мышью (необязательно)"),
    ]
    for name, why in modules:
        try:
            __import__(name)
            mark = "есть"
        except Exception as exc:  # noqa: BLE001
            mark = "НЕТ  (" + str(exc) + ")"
        add("  %-13s %-6s %s" % (name, mark, why))
    add("")

    add("Настройки СРО:")
    try:
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from src.document_generator import Project
        project = Project(ROOT)
        add("  найдено СРО: %d" % len(project.all_sro))
        for profile in project.all_sro:
            project.use_sro(profile, remember=False)
            count = len(profile.enabled_documents())
            ready = "готова" if profile.is_ready else "бланки не загружены"
            add("    - %-22s %-20s документов: %d"
                % (profile.short_name, ready, count))
    except Exception as exc:  # noqa: BLE001
        import traceback
        add("  ОШИБКА загрузки настроек: " + repr(exc))
        add(traceback.format_exc())
    add("")

    applog = os.path.join(LOGS, "app.log")
    if os.path.exists(applog):
        add("Последние строки журнала (как далеко дошёл прошлый запуск):")
        try:
            with io.open(applog, encoding="utf-8", errors="replace") as handle:
                tail = handle.readlines()[-40:]
            for line in tail:
                add("  " + line.rstrip())
        except OSError as exc:
            add("  не удалось прочитать журнал: " + str(exc))
    else:
        add("Журнала logs/app.log ещё нет — программа не доходила до запуска.")
    add("")


def save_and_open():
    try:
        if not os.path.isdir(LOGS):
            os.makedirs(LOGS)
        with io.open(REPORT, "w", encoding="utf-8") as handle:
            handle.write("\n".join(_lines) + "\n")
        add("Отчёт сохранён: " + REPORT)
    except OSError as exc:
        add("Не удалось сохранить отчёт: " + str(exc))
        return
    # Открыть отчёт СРАЗУ, до тестового окна: даже если окно потом зависнет,
    # отчёт уже перед глазами.
    try:
        if os.name == "nt":
            os.startfile(REPORT)  # noqa: S606
    except Exception:  # noqa: BLE001
        pass


def test_window():
    add("")
    add("Открываю маленькое тестовое окно...")
    add("  ВИДИТЕ окно с надписью — графика работает, дело в самой программе.")
    add("  НЕ ВИДИТЕ — проблема в графике/системе, окно не может показаться.")
    try:
        import tkinter as tk
    except Exception as exc:  # noqa: BLE001
        add("  тестовое окно НЕ открылось: нет tkinter (" + str(exc) + ")")
        return
    try:
        root = tk.Tk()
        root.title("Проверка графики")
        root.geometry("440x210")
        tk.Label(
            root,
            text=("Если вы видите это окно —\n"
                  "графика на компьютере работает.\n\n"
                  "Закройте его: диагностика окончена."),
            font=("Segoe UI", 11), justify="center").pack(expand=True, padx=20, pady=16)
        tk.Button(root, text="Закрыть", width=18, command=root.destroy).pack(pady=(0, 18))
        root.update_idletasks()
        width, height = 440, 210
        x = max(0, (root.winfo_screenwidth() - width) // 2)
        y = max(0, (root.winfo_screenheight() - height) // 3)
        root.geometry("+%d+%d" % (x, y))
        root.lift()
        try:
            root.attributes("-topmost", True)
            root.after(400, lambda: root.attributes("-topmost", False))
        except tk.TclError:
            pass
        root.focus_force()
        root.mainloop()
        add("  тестовое окно закрыто — графика работает.")
    except Exception as exc:  # noqa: BLE001
        import traceback
        add("  тестовое окно НЕ открылось: " + repr(exc))
        add(traceback.format_exc())


def main():
    collect()
    save_and_open()
    test_window()
    # Дописать в отчёт итог по тестовому окну.
    try:
        with io.open(REPORT, "w", encoding="utf-8") as handle:
            handle.write("\n".join(_lines) + "\n")
    except OSError:
        pass
    add("")
    add("Готово. Пришлите файл logs/DIAGNOSTIKA.txt или скриншот этого окна.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
