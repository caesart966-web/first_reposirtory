import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.db import Database  # noqa: E402
from core.utils import load_config  # noqa: E402


@pytest.fixture
def cfg(tmp_path):
    c = load_config(ROOT / "config.yaml")
    c["_root"] = str(tmp_path)          # все пути — во временную папку
    c["http"]["domain_delay"] = 0
    c["registry"]["page_delay"] = 0
    c["enrich"]["dadata"]["enabled"] = False
    c["enrich"]["site_search"]["enabled"] = False
    c["enrich"]["site_parse"]["enabled"] = False
    return c


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    yield d
    d.close()
