from app.core.config import Settings


def test_settings_read_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "s3cret")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    s = Settings()
    assert s.jwt_secret == "s3cret"
