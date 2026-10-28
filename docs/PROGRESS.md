# Current checkpoint — integrated web showcase (2026-10-28)

Latest scope remains the integrated HTML/CSS web showcase using FastAPI and Supabase PostgreSQL through its transaction pooler. Docker and worker isolation are deferred; isolation is UNVERIFIED. No external deployment has been performed.

## Current verification and database status

- Locked dependency sync passed. The production-only dependency sync and import check passed, including the ASGI entrypoint, dashboard template, and CSS asset; the full development environment was restored afterward.
- `uv --cache-dir .cache/uv run --locked ruff check .`: passed.
- `uv --cache-dir .cache/uv run --locked pytest --tb=short -q`: 66 passed, 1 failed, 2 skipped, with one Starlette/httpx deprecation warning. The failure is the configured live Supabase connection probe; schema/repeat-migration tests are skipped unless explicitly enabled. The full suite is not green. `uv --cache-dir .cache/uv run --locked pytest -m "not integration" --tb=short -q`: 66 passed, 3 deselected.
- The running app serves the dashboard and liveness route. Its live status reports the backend running, but DB connectivity fails, schema readiness is unverified, and `/health/ready` returns 503. The login page loads; database-backed participant operations have not been verified in this environment.
- Sanitized diagnosis: DNS and TCP reach the shared Supavisor endpoint, but PostgreSQL startup fails at tenant/user routing. Current local settings use the transaction port, transaction mode, TLS required, and project-qualified username shape. The actual endpoint/tenant pair must match the current Supabase Connect settings. No URL, hostname, project reference, username, password, or raw exception was printed; `.env` was not changed and no migrations or data writes were performed.
- A Supabase dashboard attempt was blocked by a saved browser permission setting. No other access path was used. The project owner can update `DATABASE_URL` privately from Connect → Transaction pooler, then rerun `uv --cache-dir .cache/uv run --locked pytest tests/test_database_live.py::test_live_pooler_connection -v` and `uv --cache-dir .cache/uv run --locked python -m aegislab.check_running`.

## Deployment readiness

- Render and Vercel configuration is prepared, but neither host build nor deployment has been performed. Both require production environment variables; a successful live database/schema readiness check is still a prerequisite to a working deployment. Refer to `docs/DEPLOYMENT.md` and `deploy_guide.md`.
- Production settings must include the Supabase pooler URL, transaction mode, TLS, stable signing key, production mode, and exact HTTPS public origin. For Vercel, apply migrations once from a trusted terminal and disable automatic migration at function startup.

## Commit preparation

- Source/configuration are unchanged in this cleanup. The only working-tree change is this progress-log consolidation. No secrets or generated local data are staged; no commit has been created.

---
## Live startup and endpoint check (2026-10-20)

- Started the local app with `uv --cache-dir .cache/uv run --locked uvicorn aegislab.main:app --host 127.0.0.1 --port 8000` and left it running. The dashboard is open at `http://localhost:8000/`.
- Direct HTTP checks from the running environment: `/health/live` 200; `/health/ready` 503 (`ready=false`, backend running, database error, schema unverified); `/api/status` 200 with security_validation unverified; `/` 200; `/static/dashboard.css` 200; `/api/docs` 200. Dashboard visibly reports FastAPI Running, Supabase Connection failed, Schema Not checked.
- Re-ran `uv run --locked python -m aegislab.check_running`: liveness, dashboard, CSS and API-reference checks PASS; readiness, real PostgreSQL connectivity, migration readiness and fully-ready status checks FAIL. Worker isolation remains unimplemented/UNVERIFIED.
- Startup could not reach the migration step because the actual Supabase probe failed. No schema migration or application-data write was performed by startup. No credentials or raw database errors were displayed.
- Current practical state: the web server and presentation UI run, but database-backed submission/evaluation paths are not ready in this execution environment. Repeat the database checks from the normal PowerShell environment if its network path can reach the configured Supabase transaction pooler.

---

## Submission readiness audit (2026-10-20)

- Re-read AGENTS.md and this progress log before verification. Current scope remains the integrated web showcase: Python 3.12, uv, FastAPI, HTML/CSS, Supabase PostgreSQL via transaction pooler. Docker workers and isolation remain out of scope and UNVERIFIED; no external deployment was started.
- `uv sync --locked`: passed (34 resolved, 33 packages checked). The sandbox could not write uv's default user cache, so this audit used `uv --cache-dir .cache/uv sync --locked`.
- `uv run --locked ruff check .`: passed.
- `uv run --locked pytest --tb=short -q`: 66 passed, 1 failed (`test_live_pooler_connection` could not connect to configured Supabase from this tool session), 2 skipped opt-in DB integration tests, 1 Starlette/httpx deprecation warning. Full suite is NOT green here; DB availability/schema mutations remain unverified from this environment.
- `uv run --locked python -m aegislab.check_running`: failed its HTTP smoke check because the app was not responding at `http://localhost:8000` during this audit; a separate Chrome check confirmed `net::ERR_CONNECTION_REFUSED`. No server was started and no database operation/migration was triggered. Start the app from the user's normal PowerShell, then re-run the checker to verify the actual host path.
- `git check-ignore` confirmed `.env`, `.venv`, demo accounts, and local signing/deployment keys are ignored. Git working tree was clean at `de5103d` (`main`, `origin/main`).
- No source implementation changes were needed during this audit. Existing historical live showcase/browser checks remain as recorded above; they do not replace the current failed sandbox DB probe or inactive localhost result.
- Resume locally: `uv sync --locked`, then `uv run --locked uvicorn aegislab.main:app --host 127.0.0.1 --port 8000 --reload`; in a second terminal, `uv run --locked python -m aegislab.check_running`. Do not expose `.env` or local-data during recording.

---

## Deployment walkthrough added (2026-10-15)

- Added root deploy_guide.md at the user's request, with beginner steps for local preparation, private GitHub source, Render Python Web Service settings, uv-only commands, secret entry, exact public-origin setup, hosted browser checks and troubleshooting.
- Cross-checked commands against render.yaml and the existing deployment notes; verified the PowerShell project path and paired Markdown code fences. Documentation-only change; application tests were not repeated.
- No secrets were read/displayed, no repository was pushed, and no external deployment was initiated. Existing runtime checks and blockers below are unchanged.

# Current checkpoint — integrated web showcase (2026-10-15)

Latest user authorization replaced the earlier phase-by-phase stops with one integrated prototype and explicitly deferred Docker. Earlier phase records below are historical, not the current scope. No external deployment has been authorized/performed. Supabase via transaction pooler and HTML/CSS-only server rendering remain required.

Implemented now:
- Existing four-role authentication, private validated JSON submissions, immutable digests/history and fixed evaluation locks are preserved.
- Trusted controller-side deterministic fixture runner: bounded Red prompts, Blue substring matching, fixed MOCK / mock-v1 response, real aggregate outcomes and ordered redacted events. No submitted code, container workers, network paths or worker volumes are executed/provisioned.
- Recorded completed/failed fixture outcomes, measured runtime and role-specific reports. Participants receive only their own artifact metadata plus aggregate feedback; the creating Evaluator receives all locked metadata, redacted timeline and exports.
- Deterministic event serialization, sequence/previous-event SHA-256 chain, Ed25519 signed checkpoint, safe evidence export, recorded original/modified-copy verification and an independent offline public-key verifier. Cryptography was added by the user with uv add cryptography after the sandbox blocked PyPI. uv.lock is resolved and synchronized.
- Additive 0003_web_showcase migration stores immutable terminal runs and verification records. Previously applied migrations were not edited. Trusted local startup now applies missing additive migrations under the existing advisory lock; the running host server applied 0003 and reports all three checksums/tables current.
- Local signing keys live in ignored local-data; production requires a stable environment-provided key and uses Secure cookies. Readiness checks actual DB/schema/signing-key availability. No secrets printed or exposed through the dashboard.
- Validation matrix shows actual fixture bounds, references to run events and five UNVERIFIED worker boundary rows. No simulated isolation results, marker cleanliness or universal security claims.
- Repeatable demo appends new locks/runs while reusing identical synthetic fixture versions; non-destructive scoped reset instructions preserve all existing data/history. No reset/delete endpoint was introduced.
- Render blueprint, Vercel entrypoint/configuration and private deployment-key preparation command; no remote builds or publication. Deployment remains UNVERIFIED.

Actual checks:
- uv sync --locked: passed; 34 packages resolved / 33 checked.
- uv run --locked ruff check .: passed.
- uv run --locked pytest --tb=short -q: 66 passed, 1 failed direct DB connection test, 2 skipped opt-in DB tests, 1 existing Starlette/httpx deprecation warning. Full suite is NOT green. Agent subprocess sockets to PostgreSQL remain denied; do not claim direct SQL trigger/migration reapplication tests passed.
- uv run --locked python -m aegislab.check_running: all 8 checks passed, exit 0. Running user-hosted backend reaches Supabase, reports migration 0001/0002/0003 readiness, no JavaScript and security unverified.
- uv run --locked python -m aegislab.demo_showcase: all 23 live checks passed, exit 0, through the running Supabase-backed server. Exercises all roles, private fixtures, evaluator-only execution, actual two-turn outcome (1 allowed mock call / 1 blocked), all five unexecuted worker checks UNVERIFIED, filtered Red/Blue/Client reports, participant export denial, original PASS, modified-copy FAIL, export privacy and known Blue artifact denial to Red (404).
- Initial live-demo attempt exceeded a 120-second harness timeout after 17 checks; that partial attempt was not called a pass. Re-ran without that harness deadline using durable ignored log capture; the complete 23-check run exited 0. No artificial application delays were used.
- Offline CLI original export: PASS / exit 0. Modified export: FAIL / exit 1 as intended. Unit tests additionally cover altered contents/links/signatures/manifest/outcome/checks, reordered/deleted/truncated events, wrong key/run identity and rechaining without a signing key; fixture input/output/turn/deadline failure handling and locked-document digest mismatch.
- Browser: privately signed in as Evaluator, inspected real report/matrix, tested modified-copy form (FAIL with original PASS preserved), used the HTML Run button to create another completed run, then privately signed in as Red and confirmed its report has only Red metadata and aggregate feedback, without private timeline/export controls. A browser observation timed out after modified-copy navigation; a fresh state confirmed the successful persisted rejection, so the action was not blindly repeated.
- Saved screenshots: docs/screenshots/showcase-report.png and showcase-evidence.png (synthetic IDs/digests only). No passwords, .env contents or private key material displayed.
- Git ignore checks confirmed .env, .venv and local-data credentials/signing key excluded. Staging failed: .git/index.lock Permission denied. The source and uv.lock remain preserved but uncommitted; previous Phase 1 commit 6b7c776 remains the last committed checkpoint. No permissions were bypassed.

Recording/resume:
- Full walkthrough and 2–3 minute narration: docs/RECORDING_SHOWCASE.md. Scope/visibility/limits: docs/SHOWCASE_SCOPE.md. Hosting preparation: docs/DEPLOYMENT.md. README and AGENTS reflect the new scope.
- Current CLI-prepared recording run: d215a051-1886-42b4-a1dc-f87cf542e32b, evaluation adb99dcd-e304-464a-b0ee-f9afac272910. Receipt local-data/showcase_receipt.json and offline files local-data/exports/original.json, modified.json, verification-key.pem refer to this run.
- Browser Run button also created 637d9881-55d8-463a-b72f-1ca4fe721398 against the same lock; it has its own evidence and initially unexecuted verification, correctly labeled.
- Resume: uv run --locked uvicorn aegislab.main:app --host 127.0.0.1 --port 8000 --reload. Existing server remains running. Rehearse/reset scenario: uv run --locked python -m aegislab.demo_showcase (appends fresh synthetic run, no data deletion).
- Browser left signed in as demo-evaluator on the CLI-prepared run at #verification, with Original PASS and Modified copy FAIL visible; marked to remain open. Credential objects were cleared.
- Keep .env, private local-data keys/accounts, Supabase schema, .venv and uv.lock. Do not run a second server on port 8000 while the existing one is active.
- Docker, worker isolation/cleanup, real model integration, gVisor/microVMs, CI, RAG, agents and multimodal remain outside this web showcase. Deployment config is prepared, not tested/published. Direct DB integration from the tool sandbox and Git commit remain environment blockers.

---

# Phase progress

## Phase 2 — recording checkpoint ready (2026-10-15)

User authorized Phase 2 and completed the host-side demo_setup command/server restart because the agent sandbox cannot open PostgreSQL sockets. Phase 1 is preserved at commit 6b7c776. Phase 3 is not started.

Implemented:
- Four synthetic roles with salted PBKDF2 passwords, hashed expiring sessions, HttpOnly/SameSite cookies, same-origin writes, CSRF protection and logout.
- Inert narrow JSON fixtures; no submitted code or model is executed. The Client document explicitly describes mock-v1.
- Owner-only document access, role-limited creation, canonical SHA-256 digests, immutable version history and idempotent repeated documents.
- Evaluator metadata-only coordination and evaluations locking four immutable version references. Participant evaluation views expose only their own reference.
- An additive 0002_private_versions migration with database digest constraints and update/delete/truncate rejection triggers. The previously applied 0001 migration was not edited.
- HTML/CSS workspace, private version pages, version-locking form and an actual owner-scoped access-attempt form. No JavaScript.

Actual validation:
- Real authenticated HTTP demo: 27 checks passed; process exit 0; metadata-only receipt in local-data/phase2_receipt.json. The initial background output capture missed later output, so completion was verified from the process exit and complete receipt, not inferred from partial login output.
- The demo exercised all four logins, private fixture creation/digests, duplicate reuse, own-only listing, known Blue artifact denial to Red (404), evaluator private-content denial, metadata-only coordination, role/CSRF/format rejection, evaluation locking, a distinct Red v2, preserved original references, preserved v1 content, Red-only evaluation references, absent mutation endpoint (405), and logout enforcement.
- Verified original evaluation 32e1146c-1252-4e2b-bd5c-90dc94703adc still references Red v1 fbed9bb3-78aa-40c1-8554-ad974c2ab4b5 after Red v2 f5feba99-00fc-45c3-a849-7020a8c926aa was created.
- Browser verification: Evaluator login, private policy form/idempotent reuse, version selection and evaluation creation, logout, Red login, Red v1/v2 history, known Blue denial with Observed HTTP 404, and role-filtered original evaluation page all passed.
- Browser verification caught a real form bug: no-referrer yielded opaque form Origin headers. Changed Referrer-Policy to same-origin; normal form login succeeded afterward. Opaque/cross-origin requests remain rejected, CSRF remains required, and regression coverage was added.
- Saved screenshots: docs/screenshots/phase2-evaluation.png and phase2-access-denied.png. They contain synthetic metadata only, no credentials.
- uv run --locked pytest -m "not integration": 43 passed. uv run --locked ruff check . and uv sync --locked passed.
- uv run --locked python -m aegislab.check_running: all eight live foundation/HTTP checks passed after Phase 2 integration, including readiness 200, live server-side PostgreSQL and current required tables/checksums.
- Normal full pytest from the agent sandbox: 43 passed, 1 failed direct connection test, 2 skipped opt-in database tests, 1 existing Starlette/httpx deprecation warning. The full suite is not reported green.
- With AEGISLAB_RUN_DB_TESTS=1, all three direct database checks failed at the sandbox connection restriction before schema/mutation verification. Raw driver exception chaining in a failure-reporting path was removed and sanitized output verified. DB-trigger mutation behavior remains unverified from this environment; no changes were committed by those failed tests.
- The user-started server reaches Supabase transaction pooling; agent subprocesses are denied direct sockets (Windows 10013). Authorization to use the PC did not change the sandbox network boundary. No firewall or browser protections were disabled and no database proxy/admin backdoor was added.

Recording and continuation:
- Use docs/RECORDING_PHASE_2.md and docs/PHASE_2_FORMAT.md. All Python commands use uv.
- The server is left running on localhost:8000; browser is signed in as demo-red on the verified original locked evaluation.
- Credentials remain in ignored local-data/demo_accounts.json; the loaded browser-automation credential object was cleared. .env contents and passwords were not displayed.
- Repeat demo: uv run --locked python -m aegislab.demo_phase2. Resume server: uv run --locked uvicorn aegislab.main:app --host 127.0.0.1 --port 8000 --reload.
- Preserve the Supabase schema, .env, local-data credentials, .venv and uv.lock. Repeated demos reuse identical versions and create new evaluation locks; no reset is performed.
- Docker build/startup is unverified. Worker execution/isolation, signed evidence and complete reports remain planned. These checks establish application behavior within the exercised paths, not universal security.
- Local Phase 2 commit attempt was blocked: Git could not create .git/index.lock (Permission denied). The source and updated uv.lock remain preserved in the working tree; the Phase 1 commit 6b7c776 is still the last committed checkpoint. No Git permissions were changed or bypassed.
- Stop at this checkpoint. Continue only when the user authorizes Phase 3.


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
| 2 | Authenticated roles, private submissions, fixed versions | Recording checkpoint ready; see latest verification |
| 3 | Separate container workers and bounded controller interactions | Planned |
| 4 | Real isolation validation with recorded observed outcomes | Planned |
| 5 | Signed tamper-evident evidence, independent verification, reports | Planned |
| 6 | Integrated demo, repeatable reset and narration | Planned |

Future gVisor, microVMs, CI, RAG, agents and multimodal evaluation remain outside this prototype.
