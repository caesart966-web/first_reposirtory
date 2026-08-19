# -*- coding: utf-8 -*-
"""Собрать приложение в один файл и подготовить папку для передачи коллегам.

Запускается из СОБРАТЬ_ПРИЛОЖЕНИЕ.bat (на Windows получится .exe). На Linux
тоже работает — получится исполняемый файл, это удобно для проверки сборки.

Что делает:
  1. вызывает PyInstaller и собирает ОДИН файл-программу из run.py;
  2. складывает рядом с ним папки `sro/` и `config/` (бланки и настройки) —
     программа читает их рядом с собой;
  3. кладёт короткую памятку. Готовую папку `dist/Документы-СРО` можно
     целиком передать коллеге: запуск — двойным щелчком по программе.

Папки `output/`, `logs/` и счётчик `usage.json` создаются рядом с программой
при первом запуске у пользователя.

Нужен установленный PyInstaller: `pip install pyinstaller` (батник ставит сам).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "ДокументыСРО"           # имя самого файла-программы
DIST_NAME = "Документы-СРО"          # имя папки для передачи коллегам

DIST = ROOT / "dist"
BUILD = ROOT / "build"
BIN = DIST / "_bin"
OUT = DIST / DIST_NAME

# Данные, которые едут РЯДОМ с программой (не внутри неё): бланки и настройки.
DATA_DIRS = ["sro", "config"]

# Библиотеки, которые PyInstaller иногда не находит сам.
COLLECT_ALL = ["tkinterdnd2"]


def say(text: str = "") -> None:
    print(text)
    sys.stdout.flush()


def run_pyinstaller() -> None:
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", APP_NAME,
        "--paths", str(ROOT),
        "--distpath", str(BIN),
        "--workpath", str(BUILD),
        "--specpath", str(BUILD),
    ]
    for package in COLLECT_ALL:
        try:
            __import__(package)
        except Exception:  # noqa: BLE001
            continue  # необязательная библиотека не установлена — пропускаем
        args += ["--collect-all", package]
    args.append(str(ROOT / "run.py"))
    say("Собираю программу (это может занять пару минут)...")
    subprocess.check_call(args)


def assemble() -> Path:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    exe = next(BIN.glob(APP_NAME + ".*"), None) or (BIN / APP_NAME)
    if not exe.exists():
        raise SystemExit(f"Не найден собранный файл программы в {BIN}")
    shutil.copy2(exe, OUT / exe.name)

    for name in DATA_DIRS:
        src = ROOT / name
        # _originals с исходными бланками коллегам не нужны — не копируем.
        shutil.copytree(src, OUT / name,
                        ignore=shutil.ignore_patterns("_originals", "__pycache__"))

    (OUT / "ПРОЧТИ.txt").write_text(
        "Документы для вступления в СРО\n"
        "=============================\n\n"
        "Запуск: двойной щелчок по файлу «" + APP_NAME + "».\n\n"
        "Рядом с программой должны лежать папки sro и config — не удаляйте их.\n"
        "Готовые документы появятся в папке output рядом с программой.\n"
        "Устанавливать Python и что-либо ещё не нужно.\n\n"
        "Для сохранения в PDF пригодится установленный Microsoft Word или\n"
        "LibreOffice; без них программа делает DOCX, а PDF можно сохранить\n"
        "из Word: Файл — Сохранить как — PDF.\n",
        encoding="utf-8")
    return OUT


def main() -> int:
    run_pyinstaller()
    folder = assemble()
    say()
    say("Готово. Папка для передачи коллегам:")
    say("  " + str(folder))
    say()
    say("Передайте её целиком (можно заархивировать в ZIP).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
