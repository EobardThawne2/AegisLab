# Phase 1 recording checkpoint

The live app at http://localhost:8000 was verified on 2026-10-15: backend running, real Supabase transaction-pooler connectivity, schema current at 0001_foundation, and HTTP readiness 200. Refresh checks produced a new timestamp and a newly measured latency. These are foundation checks; security controls remain UNVERIFIED.

## Prepare privately

- Keep the existing server running. Do not restart it just to run the recording check.
- Keep .env, passwords, Supabase connection strings and database administration screens off camera.
- Open http://localhost:8000 in the browser. Maximize the window; record at 100% zoom when text is readable.
- Open a clean PowerShell terminal at C:\Users\admin\Desktop\AegisLab.
- Optionally run uv sync --locked before recording. No dependency downloads occur during evaluation demos in future phases; Phase 1 has no evaluation execution yet.

If restarting is actually needed, use:

~~~powershell
uv run --locked uvicorn aegislab.main:app --host 127.0.0.1 --port 8000
~~~

If schema setup is needed on a fresh installation, privately run uv run --locked python -m aegislab.migrate first. The current running server already reports the applied schema as current.

## Capture (about 60–90 seconds)

1. In the clean terminal, run:

   uv run --locked python -m aegislab.check_running

   Expected: eight actual PASS lines for backend liveness, readiness, database probe through the running server, migration readiness, status response, dashboard, CSS and API reference. The command exits nonzero if a required check fails. It makes real requests; allow the network checks to finish naturally. The final line explicitly keeps worker isolation, participant authorization and signed evidence UNVERIFIED.

2. Switch to http://localhost:8000 and introduce AegisLab.

   Expected: pale-blue/navy/teal styling and the Phase 1 Foundation label. The architecture illustration is explicitly marked planned.

3. Scroll to System connectivity.

   Expected for the verified setup: Backend Running; Supabase PostgreSQL Connected through the transaction pooler; Schema Current with 0001_foundation. Green here refers only to these connectivity/readiness checks.

4. Click Refresh checks and show the new checked-at timestamp and measured latency.

   Expected: another real server-side PostgreSQL check. There is no JavaScript, fake progress or fixed demonstration result. Each refresh can take several seconds over the hosted database connection.

5. Show the workflow below the cards:

   Private Submissions → Version Locking → Isolated Evaluation → Evidence → Role-Specific Reports.

   Expected: all five stages show Planned and their future phase numbers. Scroll slightly farther to show Security: UNVERIFIED.

6. Optionally open API reference from the header, then return to the dashboard.

   Expected: the HTML/CSS endpoint reference loads. Avoid the footer's raw JSON link during recording: Chrome blocked raw JSON navigation in the verification session, although the same endpoint returned HTTP 200 and valid JSON to the terminal check. Do not disable browser protections or extensions for this recording.

If a check fails during capture, stop and inspect it; do not narrate it as passing. Keep .env off screen.

## Narration

"This is AegisLab's first runnable checkpoint: a FastAPI foundation with an HTML and CSS dashboard. The terminal check makes real requests to the local application. The backend reaches PostgreSQL through our Supabase transaction pooler and checks its recorded migration and foundation record. Refreshing performs another live check. These indicators establish connectivity and schema readiness. Private submissions, isolated evaluation, verifiable evidence and separated reports are planned for the following phases. We report actual boundaries tested, not impossible immunity."

## Validation limits

The running server's HTTP/application checks passed. The agent's separate direct PostgreSQL integration test was denied by sandbox networking (Windows error 10013), so it was not represented as passing. The ordinary test run from that sandbox produced 13 passed, 1 failed direct-connection check, 1 skipped opt-in schema test, plus a Starlette dependency deprecation warning. Lint and locked synchronization passed. Docker startup and participant security controls remain unverified.

To run direct schema/migration validation from your own terminal, after connectivity is available:

~~~powershell
$env:AEGISLAB_RUN_DB_TESTS = "1"
uv run --locked pytest -m integration -v
Remove-Item Env:AEGISLAB_RUN_DB_TESTS
~~~

## Leave ready

Leave the current server running for the recording. Otherwise stop it with Ctrl+C and use the resume command later. Preserve uv.lock, .venv, the private .env and the aegislab database schema. No schema reset is needed. Wait for explicit instruction before Phase 2.
