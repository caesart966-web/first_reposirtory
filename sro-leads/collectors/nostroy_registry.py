"""Реестр членов НОСТРОЙ (строители). Эндпоинты и карта полей — config.yaml: registry.nostroy."""
from .base import RegistryCollector


class NostroyRegistry(RegistryCollector):
    name = "nostroy_registry"
    source = "nostroy"
