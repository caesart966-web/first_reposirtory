# -*- coding: utf-8 -*-
"""Точка входа приложения.

Этот файл запускает окно программы. Он же — вход для сборки в один .exe
(PyInstaller собирает именно run.py). При обычной работе из исходников можно
запускать и его: `python run.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Чтобы пакет `src` находился и из исходников, и из сборки.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.gui import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
