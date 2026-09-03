from django.test import SimpleTestCase

from config.db_url import database_url_to_django


class DatabaseUrlToDjangoTests(SimpleTestCase):
    def test_asyncpg_driver_suffix_is_stripped(self) -> None:
        # docker-compose passes DATABASE_URL with the +asyncpg driver suffix used by
        # the FastAPI backend; the sync psycopg backend needs it stripped off.
        config = database_url_to_django("postgresql+asyncpg://u:p@h:5432/db")

        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["USER"], "u")
        self.assertEqual(config["PASSWORD"], "p")
        self.assertEqual(config["HOST"], "h")
        self.assertEqual(config["PORT"], "5432")
        self.assertEqual(config["NAME"], "db")

    def test_sslmode_query_param_becomes_options(self) -> None:
        # Neon (and other managed Postgres) requires ?sslmode=require in the URL.
        config = database_url_to_django("postgresql://u:p@h:5432/db?sslmode=require")

        self.assertEqual(config["OPTIONS"], {"sslmode": "require"})

    def test_sqlite_scheme_falls_back_to_in_memory(self) -> None:
        # Mirrors backend/tests/conftest.py's sqlite+aiosqlite:// fallback for tests.
        config = database_url_to_django("sqlite://")

        self.assertEqual(config["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(config["NAME"], ":memory:")
