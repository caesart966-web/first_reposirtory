from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def contacts_html() -> str:
    return (FIXTURES / "company_site.html").read_text(encoding="utf-8")
