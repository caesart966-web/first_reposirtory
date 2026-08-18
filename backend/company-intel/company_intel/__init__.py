"""company-intel — сбор данных о компании из открытых источников.

Быстрый старт из кода:

    import asyncio
    from company_intel import Query, run_pipeline

    profile = asyncio.run(run_pipeline(Query(name="ООО Ромашка", city="Москва")))
    print(profile.to_json())
"""
from .config import Config
from .models import Attribute, Finding, Profile, Provenance, Query
from .pipeline import run_pipeline
from .report import to_csv, to_markdown, to_text

__version__ = "0.1.0"
__all__ = [
    "Config", "Query", "Profile", "Finding", "Attribute", "Provenance",
    "run_pipeline", "to_markdown", "to_csv", "to_text", "__version__",
]
