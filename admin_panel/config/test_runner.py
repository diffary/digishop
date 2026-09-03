"""Test runner that lets the unmanaged `shop` app get its tables created in the test DB.

The shop models are managed=False in normal operation (see Решение 1 in the plan):
Django must never be able to create/alter/drop the real business tables via migrate.
But with MIGRATION_MODULES = {"shop": None}, the standard test DB setup has nothing to
build the shop tables from, so ORM smoke tests would have no tables to talk to.

The fix: flip `managed = True` on every shop model right before the test database is
created. `create_test_db(run_syncdb=True)` then builds tables for apps without
migrations (the normal Django path for unmigrated apps), using our model definitions
as the schema source for the *test* database only. `settings.DATABASES["default"]`
is untouched, so this only ever runs against the throwaway sqlite/test-postgres
database, never the real one.

Honest limitation (Решение 4): this only proves the Django models and the real
Postgres schema *can* agree, not that they currently do. Drift between shop/models.py
and the actual Alembic-owned schema is NOT caught by these sqlite-backed tests -- it
has to be caught by a manual `manage.py test` run against compose-postgres (Task 3).
"""

from django.apps import apps
from django.test.runner import DiscoverRunner


class UnmanagedModelTestRunner(DiscoverRunner):
    def setup_databases(self, *args, **kwargs):
        shop_models = list(apps.get_app_config("shop").get_models())
        for model in shop_models:
            model._meta.managed = True
        try:
            return super().setup_databases(*args, **kwargs)
        finally:
            # Flip back to managed=False once the test tables exist, so tests still
            # observe (and can assert on) the real, unpatched managed=False contract.
            for model in shop_models:
                model._meta.managed = False
