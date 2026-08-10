"""Коннекторы источников данных.

Каждый источник — отдельный модуль с классом-наследником BaseConnector.
Импорт модулей здесь регистрирует их в реестре (см. base.register_connector);
добавление нового источника = новый файл + одна строка импорта ниже,
правок ядра не требуется.
"""
from connectors import base  # noqa: F401
from connectors import egrul_fns  # noqa: F401
from connectors import zakupki  # noqa: F401
from connectors import sro  # noqa: F401
from connectors import website  # noqa: F401
from connectors import dgis  # noqa: F401
from connectors import yandex_maps  # noqa: F401
from connectors import dadata  # noqa: F401
from connectors import domain_search  # noqa: F401

from connectors.base import CONNECTOR_REGISTRY, BaseConnector, build_connectors

__all__ = ["CONNECTOR_REGISTRY", "BaseConnector", "build_connectors"]
