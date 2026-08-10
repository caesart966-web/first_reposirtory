"""Источники контактов.

Каждый источник — функция source(company, fetcher, cfg) -> list[Found].
Реестр SOURCES перечисляет их в порядке приоритета. Легко добавить свой:
написать функцию и дописать её в SOURCES.
"""
from __future__ import annotations

from .aggregators import aggregator_cards
from .apis import checko_api, datanewton_api
from .company_site import company_site
from .directories import map_directories

# Порядок = приоритет. Сначала структурные API (точно и в один запрос),
# затем бесплатные веб-источники. Источник без ключа сам себя пропускает.
SOURCES = [
    checko_api,         # Checko API — контакты сразу привязаны к ИНН
    datanewton_api,     # Datanewton API — запасной структурный источник
    aggregator_cards,   # карточки агрегаторов по прямым URL
    company_site,       # официальный сайт компании
    map_directories,    # 2ГИС/Яндекс.Карты/Zoon по названию и адресу
]

__all__ = [
    "SOURCES", "checko_api", "datanewton_api",
    "aggregator_cards", "company_site", "map_directories",
]
