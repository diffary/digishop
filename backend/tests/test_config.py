import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_read_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "s3cret-long-enough-16")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    s = Settings()
    assert s.jwt_secret == "s3cret-long-enough-16"


def test_settings_rejects_short_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "too-short")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    with pytest.raises(ValidationError):
        Settings()
