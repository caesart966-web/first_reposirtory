import pytest

from construction_mcp.db import Database


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()
