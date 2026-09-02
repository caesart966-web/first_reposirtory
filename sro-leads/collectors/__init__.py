"""Коллекторы сигналов. Новый коллектор = один файл в этой папке с подклассом Collector.

Обнаружение автоматическое: модуль импортируется, берутся классы с непустым `name`.
Включение/порядок — в config.yaml (collectors.enabled).
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Type

from .base import Collector


def discover() -> dict[str, Type[Collector]]:
    found: dict[str, Type[Collector]] = {}
    for mod_info in pkgutil.iter_modules(__path__):
        if mod_info.name.startswith("_") or mod_info.name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{mod_info.name}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Collector) and cls is not Collector and getattr(cls, "name", ""):
                if cls.__module__ == module.__name__:
                    found[cls.name] = cls
    return found
