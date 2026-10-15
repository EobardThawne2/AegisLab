# Phase progress

## Phase 1 — running checkpoint verified for recording; environment limits below




## Running application verification — 2026-10-15

- User's existing server at http://localhost:8000 remained running throughout; it was not restarted into the tool sandbox.
- Browser verification showed Backend Running, Supabase PostgreSQL Connected (transaction pooler), and Schema Current with migration 0001_foundation.
- Refresh checks changed the UTC timestamp from 11:46:33 to 11:46:43 and measured a new live database latency. Observed warm checks were about 3 seconds; first check was about 6.5 seconds.
- HTTP /health/live returned 200. HTTP /health/ready returned 200 with ready=true, database.status=connected, schema_status=ready, and migration 0001_foundation. This is actual server-side database evidence, not a mocked status.
- Added uv run --locked python -m aegislab.check_running. All eight real HTTP/application smoke checks passed: liveness, readiness, server-side PostgreSQL probe, migration readiness, status JSON, dashboard/no-JavaScript labels, CSS asset, and HTML/CSS API reference.
- The checker explicitly uses the already-running server; it does not replace or hide the direct-driver integration test.
- uv run --locked ruff check . and uv sync --locked passed.
- The agent-sandbox pytest run remains 13 passed, 1 failed direct DB connection check, 1 skipped opt-in schema/migration test, and 1 Starlette dependency deprecation warning. Outbound direct PostgreSQL sockets from that sandbox are denied; the user-started application reaches Supabase successfully. Do not call the full pytest suite passed from the agent environment.
- The schema exists and its recorded digest/foundation record were verified through the running backend. A direct repeat-migration integration run was not completed from this sandbox.
- Browser layout was inspected at the actual viewport: connectivity cards and planned workflow are readable with normal scrolling. Security remains UNVERIFIED. No worker, auth or evidence capabilities were added.
- Chrome blocked direct navigation to raw /api/status JSON with ERR_BLOCKED_BY_CLIENT. The terminal smoke check obtained valid HTTP 200 JSON from it. The recording guide uses the terminal check and dashboard instead; no browser protection was disabled.
- The private .env already labeled the pooler as transaction and needed no changes. No credentials or raw connection strings were displayed.
- Local Git was initialized; .env, .venv and .cache ignore rules were checked. The checkpoint preserves uv.lock. No remote was created and nothing was published.
- README and the Phase 1 recording guide now contain exact resume commands, eight-check verification, a 60–90 second capture sequence and narration.

Ready: leave the existing server running, record Phase 1 with docs/RECORDING_PHASE_1.md, then wait for explicit next-phase authorization. Docker/container startup and all participant security controls remain unverified. Direct-driver/schema integration tests can be run from the user's own terminal using the documented opt-in command.

## Previous live connection testing — 2026-10-15

- User requested that database connectivity be tested.
- Added test_live_pooler_connection: it runs a real, read-only pooler/database probe whenever DATABASE_URL is configured. A configured connection failure FAILS; it is not skipped. Missing configuration explicitly skips as unverified.
- The existing schema/migration integration test remains opt-in (AEGISLAB_RUN_DB_TESTS=1).
- Ran the opt-in schema test: it failed on its connection prerequisite; no migrations executed.
- Diagnostic results: DNS resolved, but a TCP connection attempt was denied with Windows WSAEACCES 10013 (errno 13) inside this sandbox. The PostgreSQL driver also reported a socket-access failure. This does not establish whether the user's normal terminal can connect.
- Non-secret configuration mismatch: the URI uses transaction-pooler port 6543, while DATABASE_POOLER_MODE=session. The private .env was not changed; set DATABASE_POOLER_MODE=transaction to label the actual endpoint accurately. Automatic prepared statements are already disabled for both modes.
- uv run --locked pytest --tb=short: 1 failed (real DB connectivity), 13 passed, 1 skipped (schema/migration opt-in), 1 dependency deprecation warning. This is an actual failing live check, not a successful connection or a security check.
- uv run --locked ruff check . passes.
- README and AGENTS.md now document automatic configured-DB testing. No credentials, URI, raw database exceptions, or private .env contents were exposed.

Next: run uv run --locked pytest tests/test_database_live.py::test_live_pooler_connection -v in the user's own terminal, which is outside this tool sandbox. After real connectivity passes, apply/check migrations and run the opt-in schema test. Phase 1 is still pending its fully validated recording checkpoint.

## Prior verification — 2026-10-15

- Reproduced uv run --locked pytest: collection failed with ModuleNotFoundError for aegislab.
- Fixed pytest import discovery with pythonpath = ["."] in pyproject.toml; this project intentionally uses tool.uv.package = false.
- Added explicit Ruff exclusions for .cache, .venv and local-data. Without a Git repository, the lint walk included downloaded dependency source despite .gitignore.
- Updated UTC timestamp code to satisfy the installed Ruff version.
- uv run --locked pytest now passes: 13 passed, 1 skipped, 1 warning. The skipped live database integration test remains unverified. The warning is Starlette's httpx TestClient deprecation notice; it does not fail the suite and has not been suppressed.
- uv run --locked ruff check . passes.
- uv sync --locked succeeds. uv.lock and installed dependencies now exist; the original dependency-installation blocker below is historical.
- A private .env now exists; its contents were not displayed or modified.
- A real, read-only database_status probe returned Connection failed / schema unverified in this execution environment. Its cause is not established. No tables were created or changed during this test-fix task.
- Docker and browser recording validation remain pending. No later phase has begun.

Next: establish successful pooler connectivity, apply/check migrations, run the opt-in live database test, and validate the browser recording checkpoint. Then preserve/commit uv.lock and stop for Phase 1 recording.

## Initial setup history — 2026-10-14

Source created: FastAPI routes, server-rendered HTML/CSS dashboard, PostgreSQL driver integration, initial SQL migration, uv project configuration, Docker configuration, environment example, checks and recording guide.

Actual observations on 2026-10-14:
- Workspace was empty; no existing Git repository or applicable AGENTS.md found.
- uv 0.12.5 and Python 3.12.1 are installed.
- uv venv .venv succeeded using a workspace-scoped cache.
- uv add failed: sandbox TCP access to PyPI was denied (Windows error 10013).
- Runtime/development dependencies were recorded in pyproject.toml with uv add --frozen and uv add --dev --frozen. This declaration-only option did not resolve or install them.
- Python syntax validation passed: uv run --no-sync python -m compileall -q aegislab tests.
- uv sync --offline also failed: FastAPI is not in the local cache.
- uv run --no-sync python -m pytest could not execute tests: pytest is not installed. This is a blocked check, not a pass.
- uv.lock, dependency installation, app startup and test execution are not yet validated.
- No DATABASE_URL was configured when first checked. Live Supabase connection and migration are UNVERIFIED.
- Docker client 29.6.1 is installed; Docker daemon pipe unavailable. Image build and compose startup are UNVERIFIED.
- The normal shell tool fails during Windows sandbox setup. The alternate local Node runtime can inspect files and execute local commands.

Original resume plan (dependency setup and unit checks are now completed; see latest verification):
1. Run uv sync, then uv sync --locked from the workspace in a terminal with PyPI network access. Dependencies are already declared using uv.
2. Set DATABASE_URL privately in .env using the Supabase pooler URI.
3. Run uv run --locked ruff check . and uv run --locked pytest; fix issues.
4. Run uv run --locked python -m aegislab.migrate twice; verify apply/no-op behavior.
5. Run opt-in integration tests and uv run --locked uvicorn aegislab.main:app --host 127.0.0.1 --port 8000.
6. Inspect the real dashboard in a browser and verify startup, status, failure handling and lack of secrets.
7. Update this record with actual results; initialize Git and commit source and uv.lock without .env/.venv/.cache.
8. Stop for Phase 1 recording. Wait for explicit authorization for the next phase.

## Later phases — not started

| Phase | Scope | Status |
| --- | --- | --- |
| 2 | Authenticated roles, private submissions, fixed versions | Planned |
| 3 | Separate container workers and bounded controller interactions | Planned |
| 4 | Real isolation validation with recorded observed outcomes | Planned |
| 5 | Signed tamper-evident evidence, independent verification, reports | Planned |
| 6 | Integrated demo, repeatable reset and narration | Planned |

Future gVisor, microVMs, CI, RAG, agents and multimodal evaluation remain outside this prototype.
