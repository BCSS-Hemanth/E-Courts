import pytest
from app.config import settings

@pytest.fixture(autouse=True)
def configure_mock_mode():
    orig = settings.ECOURTS_MOCK_MODE
    settings.ECOURTS_MOCK_MODE = True
    yield
    settings.ECOURTS_MOCK_MODE = orig
