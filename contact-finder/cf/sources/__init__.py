"""Источники контактов.

Каждый источник — функция source(company, fetcher, cfg) -> list[Found].
Реестр SOURCES перечисляет их в порядке приоритета. Легко добавить свой:
написать функцию и дописать её в SOURCES.
"""
from __future__ import annotations

from .aggregators import aggregator_cards
from .company_site import company_site
from .directories import map_directories

# Порядок = приоритет вывода. Прямой сайт компании — самый ценный источник.
SOURCES = [
    aggregator_cards,   # rusprofile/checko/list-org/audit-it по прямым URL
    company_site,       # найти официальный сайт и снять контакты с /contacts
    map_directories,    # 2ГИС/Яндекс.Карты/zoon по названию+адресу
]

__all__ = ["SOURCES", "aggregator_cards", "company_site", "map_directories"]
