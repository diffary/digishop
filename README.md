# DigiShop

## Admin panel

`admin_panel/` is a standalone Django back-office running against the same PostgreSQL
database as the FastAPI backend. It lets staff edit product price/file_key/is_active
(closing a known gap: the seed script's skip-if-exists never updates `file_key` on
existing products), browse orders read-only, and list users read-only.

Alembic (in `backend/`) remains the sole owner of the business schema. All `shop`
Django models are declared `managed = False` and only read the existing tables;
`MIGRATION_MODULES = {"shop": None}` makes it impossible for Django to generate or run
migrations against them. Django owns only its own service tables (`django_*`, `auth_*`)
in the same database — no name collisions with the shop tables. The public API is
untouched; it stays on FastAPI.

### Run it

```
docker compose up admin
```

Then open http://localhost:8001/admin/ and log in with the bootstrap superuser.

### Superuser bootstrap

On container start, `docker-entrypoint.sh` runs `manage.py migrate` (creates only the
Django service tables) and then `manage.py createsuperuser --noinput`, which reads:

- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

The step is idempotent (`|| true`) so it's safe to re-run on every deploy. Dev values
are set directly in `docker-compose.yml`; for a Render deployment, set these (plus
`DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`) as environment variables
in the Render service settings rather than committing real credentials.
