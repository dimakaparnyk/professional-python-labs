import pytest
from fastapi.testclient import TestClient

from inventory_service.api import create_app
from inventory_service.config import Settings


def test_env(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "DATABASE_URL", "sqlite:///" + (tmp_path / "production.db").as_posix()
    )
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "warning")
    assert Settings.from_env().log_level == "WARNING"
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200


@pytest.mark.parametrize(
    "key,value",
    [("APP_ENV", "wrong"), ("LOG_LEVEL", "SECRET"), ("DATABASE_URL", "invalid")],
)
def test_bad_env(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        Settings.from_env()
