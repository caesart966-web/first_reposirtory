# -*- coding: utf-8 -*-
"""Где искать файлы программы.

Программа работает в двух видах:

  * из исходников — тогда корень это папка проекта (на уровень выше `src`);
  * собранной в один .exe (PyInstaller) — тогда корень это папка, где лежит
    сам .exe. Рядом с ним едут `sro/` и `config/`, туда же пишутся `output/`,
    `logs/` и счётчик использования.

Всё чтение и запись файлов программы отсчитывается от `app_root()`, поэтому
и из исходников, и из .exe пути получаются одинаково предсказуемыми.
"""

from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Корень приложения — папка, от которой ищутся sro/, config/, output/."""
    if getattr(sys, "frozen", False):
        # Собрано PyInstaller: рядом с .exe лежат данные и пишется вывод.
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
