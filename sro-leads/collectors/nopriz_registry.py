"""Реестр членов НОПРИЗ (проектирование и изыскания). Настройки — config.yaml: registry.nopriz."""
from .base import RegistryCollector


class NoprizRegistry(RegistryCollector):
    name = "nopriz_registry"
    source = "nopriz"
