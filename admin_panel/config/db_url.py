"""Parse a SQLAlchemy-style DATABASE_URL into a Django DATABASES["default"] dict.

The same DATABASE_URL env var is shared with the FastAPI backend (see
backend/app/core/config.py), which uses the async postgresql+asyncpg driver. Django's
sync psycopg backend needs the driver suffix stripped. ?sslmode=... (used by managed
Postgres providers such as Neon) is passed through as connection OPTIONS. An empty or
sqlite:// URL falls back to an in-memory sqlite database, mirroring the sqlite+aiosqlite://
fallback used by backend/tests/conftest.py.
"""

from urllib.parse import parse_qs, urlsplit


def database_url_to_django(url: str) -> dict:
    parts = urlsplit(url)
    scheme = parts.scheme.split("+")[0]  # e.g. "postgresql+asyncpg" -> "postgresql"

    if scheme == "sqlite":
        name = parts.path.lstrip("/") or ":memory:"
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": name,
        }

    query = parse_qs(parts.query)
    options = {key: values[0] for key, values in query.items()}

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parts.path.lstrip("/"),
        "USER": parts.username or "",
        "PASSWORD": parts.password or "",
        "HOST": parts.hostname or "",
        "PORT": str(parts.port) if parts.port else "",
        "OPTIONS": options,
    }
