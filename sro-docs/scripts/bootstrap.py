# -*- coding: utf-8 -*-
"""Подготовка рабочего окружения при первом запуске.

Запускается из START.bat СИСТЕМНЫМ Python — до того, как появилось
собственное окружение программы. Поэтому здесь только стандартная
библиотека и синтаксис, понятный старым версиям Python.

Весь текст для пользователя печатается отсюда, а не из bat-файла:
Windows не умеет надёжно читать русские буквы внутри bat-файлов.
"""

from __future__ import print_function

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = os.path.join(ROOT, ".venv")
STAMP = os.path.join(VENV, "installed.txt")

if os.name == "nt":
    VENV_PYTHON = os.path.join(VENV, "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(VENV, "bin", "python")

MIN_VERSION = (3, 9)


def say(text=""):
    print(text)
    sys.stdout.flush()


def fingerprint():
    """Отпечаток списков библиотек — чтобы переустанавливать их при изменении."""
    digest = hashlib.sha256()
    for name in ("requirements.txt", "requirements-optional.txt"):
        path = os.path.join(ROOT, name)
        if os.path.exists(path):
            with open(path, "rb") as handle:
                digest.update(handle.read())
    return digest.hexdigest()


def already_installed():
    if not os.path.exists(VENV_PYTHON) or not os.path.exists(STAMP):
        return False
    try:
        with open(STAMP, "r") as handle:
            return handle.read().strip() == fingerprint()
    except OSError:
        return False


def pip(args, quiet=True):
    command = [VENV_PYTHON, "-m", "pip"] + list(args)
    if quiet:
        command.append("--quiet")
    return subprocess.call(command)


def fail(title, lines):
    say()
    say("=" * 62)
    say("  " + title)
    say("=" * 62)
    say()
    for line in lines:
        say("  " + line)
    say()
    return 1


def main():
    if sys.version_info < MIN_VERSION:
        return fail("Слишком старая версия Python", [
            "Установлен Python %d.%d, а нужен %d.%d или новее."
            % (sys.version_info[0], sys.version_info[1],
               MIN_VERSION[0], MIN_VERSION[1]),
            "",
            "Что делать:",
            "  1. Откройте https://www.python.org/downloads/",
            "  2. Скачайте и установите свежую версию.",
            "  3. При установке поставьте галочку «Add Python to PATH».",
            "  4. Запустите START.bat снова.",
        ])

    if already_installed():
        return 0

    say()
    say("=" * 62)
    say("  Документы для вступления в СРО")
    say("=" * 62)
    say()
    say("Первый запуск: готовлю программу к работе.")
    say("Это займёт 1-2 минуты и потребует интернет. Подождите, пожалуйста.")
    say()

    if not os.path.exists(VENV_PYTHON):
        say("  [1 из 3] Создаю рабочее окружение...")
        if subprocess.call([sys.executable, "-m", "venv", VENV]) != 0:
            return fail("Не удалось создать рабочее окружение", [
                "Возможные причины:",
                "  - на диске нет свободного места;",
                "  - папка защищена от записи;",
                "  - антивирус блокирует создание файлов.",
                "",
                "Попробуйте распаковать программу в простую папку,",
                "например C:\\SRO, и запустить START.bat оттуда.",
            ])

    say("  [2 из 3] Устанавливаю необходимые библиотеки...")
    pip(["install", "--upgrade", "pip"])
    if pip(["install", "-r", os.path.join(ROOT, "requirements.txt")]) != 0:
        say()
        say("  Не получилось тихо, пробую ещё раз с подробным выводом...")
        if pip(["install", "-r", os.path.join(ROOT, "requirements.txt")],
               quiet=False) != 0:
            return fail("Не удалось установить библиотеки", [
                "Чаще всего причина - нет доступа в интернет либо его",
                "блокирует антивирус или корпоративная сеть.",
                "",
                "Что попробовать:",
                "  1. Проверьте интернет в браузере.",
                "  2. Запустите с другой сети (например, с телефона).",
                "  3. Если сеть корпоративная - попросите системного",
                "     администратора разрешить доступ к pypi.org.",
            ])

    say("  [3 из 3] Устанавливаю дополнительные возможности (PDF, перетаскивание)...")
    if pip(["install", "-r", os.path.join(ROOT, "requirements-optional.txt")]) != 0:
        say("      Не установились - это не страшно, программа работает и без них.")
        say("      PDF можно будет сделать из Word: Файл - Сохранить как - PDF.")

    try:
        with open(STAMP, "w") as handle:
            handle.write(fingerprint())
    except OSError:
        pass

    say()
    say("Всё готово. Запускаю программу...")
    say()
    return 0


if __name__ == "__main__":
    sys.exit(main())
