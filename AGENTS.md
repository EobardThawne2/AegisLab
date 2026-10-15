# AegisLab working instructions

## Authorized scope and phase boundaries
- Latest user authorization: integrate the web showcase in one go; earlier phase stops are superseded.
- Docker is deferred at the user's request. Use deterministic data fixtures; never claim worker isolation.
- Read docs/PROGRESS.md before further work. Prepare Render/Vercel configuration but do not publish externally.
- Database: Supabase PostgreSQL through its connection pooler. No local PostgreSQL fallback.
- Dashboard: HTML and CSS only for now; server-rendered through FastAPI. No JavaScript.
- Use a local CPU-friendly prototype. Do not publish externally.

## Python dependency and execution rules
- Use uv exclusively: uv venv .venv, uv add, uv add --dev, uv sync, uv run.
- Never use pip, pip3, uv pip, requirements.txt, global installs, or an unrelated environment.
- Preserve and commit uv.lock. Use uv sync --locked for reproducibility and Docker builds.
- All Python commands, tests, scripts, migrations and app startup must use uv run.
- Python support is declared in pyproject.toml and .python-version (3.12).
- .venv, .cache, local-data and secrets must remain Git-ignored.
- If the sandbox cannot write uv's default cache, use UV_CACHE_DIR inside .cache/uv.

## Truthful status and trust boundaries
- Dashboard statuses must reflect executed operations. No simulated green checks.
- Web showcase adds bounded controller-side mock fixtures, evidence and reports. Worker isolation remains unimplemented and UNVERIFIED.
- A connection check is not a security validation. Keep security status UNVERIFIED.
- Never run participant submissions on the host if Docker fails.
- Non-root containers and a rootless daemon are separate properties.
- Host, controller, administrators and signing keys belong to the trusted boundary.
- Never print DATABASE_URL, raw database exceptions, passwords or private artifacts.
- .env belongs to the user. Do not display its contents in tool output or recordings.
- Do not change previously applied SQL migrations; append a new migration.
- Keep database operations scoped to the aegislab schema; no deletion of existing project data.

## Verification and handoff
- Run uv run ruff check ., uv run pytest, and the real configured database check when possible.
- The read-only DB connection test runs when DATABASE_URL is configured, per the user’s request. Schema/migration tests remain opt-in. Skipped tests are unverified, never claimed as passing.
- Record actual checks, environment blockers and resume steps in docs/PROGRESS.md.
- Preserve the pale-blue/navy/teal style with restrained red accents.
