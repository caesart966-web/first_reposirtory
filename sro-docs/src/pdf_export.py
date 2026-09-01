# -*- coding: utf-8 -*-
"""Создание PDF из готового DOCX.

Всё локально, ничего никуда не отправляется. Два способа, по порядку:

  1. Microsoft Word, установленный на компьютере (через docx2pdf).
     Даёт вёрстку, полностью совпадающую с DOCX, — это основной способ.
  2. LibreOffice, если он установлен.
     Вёрстка близка, но в сложных бланках может немного отличаться,
     поэтому программа об этом предупреждает.

Если ни того, ни другого нет — PDF просто не создаётся. Это не ошибка:
DOCX уже готов, и его можно сохранить в PDF из Word командой
«Файл → Сохранить как → PDF».
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from . import app_logging

LIBREOFFICE_NAMES = ("soffice", "soffice.exe", "libreoffice")
LIBREOFFICE_WINDOWS_PATHS = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)


def find_libreoffice() -> str | None:
    for name in LIBREOFFICE_NAMES:
        found = shutil.which(name)
        if found:
            return found
    if sys.platform.startswith("win"):
        for path in LIBREOFFICE_WINDOWS_PATHS:
            if Path(path).exists():
                return path
    return None


def _convert_with_word(paths: list[Path]) -> list[Path]:
    """Конвертация установленным Microsoft Word (только Windows)."""
    from docx2pdf import convert  # импорт внутри: библиотека нужна не всем

    created: list[Path] = []
    for path in paths:
        target = path.with_suffix(".pdf")
        convert(str(path), str(target))
        if target.exists():
            created.append(target)
    return created


def _convert_with_libreoffice(paths: list[Path], executable: str) -> list[Path]:
    created: list[Path] = []
    for path in paths:
        command = [executable, "--headless", "--norestore",
                   "--convert-to", "pdf", "--outdir", str(path.parent), str(path)]
        subprocess.run(command, check=True, capture_output=True, timeout=180)
        target = path.with_suffix(".pdf")
        if target.exists():
            created.append(target)
    return created


def convert_many(paths: list[Path]) -> tuple[list[Path], str]:
    """Сделать PDF рядом с DOCX. Возвращает (созданные файлы, пояснение)."""
    log = app_logging.get()
    paths = [Path(p) for p in paths if Path(p).exists()]
    if not paths:
        return [], ""

    if sys.platform.startswith("win"):
        try:
            created = _convert_with_word(paths)
            if created:
                return created, ""
        except ImportError:
            log.debug("docx2pdf не установлен")
        except Exception as exc:  # Word может быть не установлен или занят
            log.warning("Не удалось создать PDF через Word: %s", exc)

    executable = find_libreoffice()
    if executable:
        try:
            created = _convert_with_libreoffice(paths, executable)
            if created:
                return created, (
                    "PDF создан через LibreOffice. Вёрстка очень близка к DOCX, "
                    "но перед подачей сравните PDF с документом Word."
                )
        except subprocess.TimeoutExpired:
            log.warning("LibreOffice не ответил вовремя")
        except Exception as exc:
            log.warning("Не удалось создать PDF через LibreOffice: %s", exc)

    return [], (
        "PDF не создан: на компьютере не найден ни Microsoft Word, ни LibreOffice. "
        "Документы Word готовы — при необходимости сохраните их в PDF командой "
        "«Файл → Сохранить как → PDF»."
    )
