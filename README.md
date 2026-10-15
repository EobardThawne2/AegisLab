# AegisLab

Local infrastructure prototype for adversarial AI safety testing, proposed for Hack in Hills 2026, PS 04: Bayora. Team lead: Ayush Mittal, DSEU Okhla.

Phase 1 provides a FastAPI backend, an HTML/CSS dashboard, Supabase PostgreSQL pooler integration and an initial versioned SQL migration. It does not implement participant authentication, workers, private submissions, evidence signing or role-specific reports. The model is planned as a mock.

**Current validation state:** see [docs/PROGRESS.md](docs/PROGRESS.md). Source creation does not establish runnable or security-tested status.

## Local setup (PowerShell)

Prerequisites: uv, Python 3.12, and an existing Supabase PostgreSQL project with a pooler URI. Docker is optional for container startup. All Python commands use uv; do not activate or reuse an unrelated environment.

Dependencies are declared through uv and pinned in uv.lock. For a fresh local setup:

~~~powershell
Set-Location C:\Users\admin\Desktop\AegisLab
$env:UV_CACHE_DIR = "$PWD\.cache\uv"
# .venv has already been created; on a fresh checkout, run:
uv venv .venv --python 3.12
uv sync --locked
~~~

Future installations use uv sync --locked. Do not regenerate the lock unnecessarily; preserve pyproject.toml and uv.lock together.

Copy .env.example to .env and edit .env privately:

~~~powershell
Copy-Item .env.example .env
~~~

Take the database URI from Supabase > Connect > Session pooler or Transaction pooler. Use DATABASE_POOLER_MODE to label the matching mode. Percent-encode reserved characters in the URI password. Do not place the URI in terminal history, screenshots or chat. No Supabase anon key/service key is needed; the backend uses the PostgreSQL driver, not the browser Data API.

Encrypted connections are required. DATABASE_SSLMODE=require encrypts transport; it does not establish full server identity verification. For certificate and hostname validation, set verify-full and DATABASE_SSLROOTCERT to a trusted Supabase CA certificate path. That stronger configuration must be tested separately.

Automatic prepared statements are disabled, and operations do not depend on retained session state. The migration lock and query timeouts are transaction-scoped. Both pooler modes are intended to work, but only modes actually tested may be called verified. A fresh connection is opened per check; this is adequate for a small recording prototype, not a load-tested design.

## Start and resume

~~~powershell
uv sync --locked
uv run --locked python -m aegislab.migrate
uv run --locked uvicorn aegislab.main:app --host 127.0.0.1 --port 8000
~~~

Open http://127.0.0.1:8000. Stop with Ctrl+C. Resume with the same startup command; the migration is idempotent and reports "Schema already current" when unchanged.

Without .env the dashboard runs with database "Not configured", schema "Not checked" and readiness HTTP 503. It never fakes database success. Editing .env then refreshing triggers a new real check unless an environment variable overrides the file.

Endpoints:

| Endpoint | Behavior |
| --- | --- |
| / | HTML/CSS dashboard; runs a real database check at page load |
| /health/live | Backend liveness only; HTTP 200 when served |
| /api/status | Actual backend/database/schema status; no credentials |
| /health/ready | HTTP 200 only when DB and migration check pass; otherwise 503 |
| /api/docs | HTML/CSS API reference; no JavaScript or external assets |

The dashboard itself uses no JavaScript, external fonts, CDNs or analytics. Refresh checks is a normal page navigation. Connectivity success is separate from security validation, which remains UNVERIFIED.

## Migration scope

uv run python -m aegislab.migrate creates only the aegislab schema, schema_migrations and foundation_metadata. Migration digests detect accidental changes to applied migration files; these are not evaluation evidence signatures. It creates no participant data. All changes run in a transaction; no tables are dropped. The database account must be allowed to create the schema and read/write its tables. Existing Supabase schemas are left alone. RLS is enabled with no participant policies; this is not a tested participant access-control implementation.

## Checks

For the already-running application, this read-only smoke check exercises HTTP endpoints, the real server-side PostgreSQL probe, schema readiness, dashboard assets and API reference:

~~~powershell
uv run --locked python -m aegislab.check_running
~~~

This command tests the existing server at http://localhost:8000. It does not connect to PostgreSQL directly: database queries execute in the running server. It is separate from direct-driver integration tests below. On 2026-10-15 all eight HTTP/application checks passed; the agent sandbox still denied outbound PostgreSQL sockets while the user-started server connected successfully.


~~~powershell
uv run --locked ruff check .
uv run --locked pytest
# Connection-only check (automatically included above when DATABASE_URL is configured):
uv run --locked pytest tests/test_database_live.py::test_live_pooler_connection -v
# Opt in to schema/migration checks after applying the migration:
$env:AEGISLAB_RUN_DB_TESTS = "1"
uv run --locked pytest -m integration -v
Remove-Item Env:AEGISLAB_RUN_DB_TESTS
~~~

The read-only connection test runs automatically whenever DATABASE_URL is configured in .env or the environment. An unreachable or invalid configured database fails the suite; it is not skipped. Without DATABASE_URL it explicitly skips as unverified. To intentionally run only tests that do not require the database, use uv run --locked pytest -m "not integration". The separate schema/migration test remains opt-in through AEGISLAB_RUN_DB_TESTS=1 and requires migrations first. Skips are never reported as successful database checks. Automated failure-path tests use controlled doubles and do not validate Supabase connectivity or container isolation.

## Optional Docker startup

The image uses uv venv, uv sync --locked --no-dev, and uv run. Dependencies install at build time. It excludes .env, .venv and local cache from the build context. There is no Docker socket or participant worker in Phase 1.

~~~powershell
docker compose build
docker compose run --rm controller uv run --locked --no-sync python -m aegislab.migrate
docker compose up -d
docker compose logs --tail 20 controller
# Stop while preserving the Supabase database:
docker compose down
~~~

The app port is bound to loopback. Credentials come from .env at runtime; do not display compose config output in recordings. Docker's daemon was unavailable during initial setup; builds and container startup remain unverified until executed. Application container configuration does not prove participant worker isolation.

## Recording and next phases

Use [docs/RECORDING_PHASE_1.md](docs/RECORDING_PHASE_1.md). Keep .env and database credentials off screen. Preserve .venv, uv.lock and the database schema for the next phase. Do not start Phase 2 automatically.

Sources for configuration: [Supabase connection guidance](https://supabase.com/docs/guides/database/connecting-to-postgres), [Psycopg prepared statements](https://www.psycopg.org/psycopg3/docs/advanced/prepare.html), [uv locked synchronization](https://docs.astral.sh/uv/concepts/projects/sync/), [uv in Docker](https://docs.astral.sh/uv/guides/integration/docker/).
