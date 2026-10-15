# AegisLab

A web showcase for adversarial AI evaluation provenance. Team Lead: Ayush Mittal, DSEU Okhla. Python 3.12, FastAPI, Supabase PostgreSQL pooler, server-rendered HTML/CSS. No JavaScript or Docker required for this checkpoint.

Works now: four authenticated synthetic roles; private validated JSON submissions; immutable version digests and evaluation locks; bounded Red/Blue/mock-model fixtures; recorded timelines; role-specific reports; hash-linked events; Ed25519-signed evidence export and offline verification; rejection of a modified evidence copy.

Execution mode is explicitly fixture_no_isolation. Fixtures are data interpreted by the trusted controller. No participant code, real model or isolated worker is executed. All five worker-isolation checks remain UNVERIFIED.

## Local startup

From this directory in PowerShell, with uv installed:

~~~powershell
# Only on first setup if .venv does not exist:
uv venv .venv
uv sync --locked
# Configure .env privately from .env.example, using the Supabase pooler.
uv run --locked python -m aegislab.demo_setup
uv run --locked uvicorn aegislab.main:app --host 127.0.0.1 --port 8000 --reload
~~~

Open http://localhost:8000. Existing setup: keep the running server, or resume with the uvicorn command above. Local startup applies missing additive migrations, checks existing migration hashes and creates an ignored local signing key if absent. It never resets existing data. A failed setup is logged without credentials; readiness and failed operations stay visible.

Demo credentials are in ignored local-data/demo_accounts.json. Read them privately before recording. Passwords are never displayed by setup or demo commands. Keep .env, .venv, .cache, local-data and signing keys out of source control. Windows file permissions rely on the user's private workspace ACL; POSIX key creation uses mode 0600.

## Repeatable recording setup

With the server running, in another terminal:

~~~powershell
uv run --locked python -m aegislab.check_running
uv run --locked python -m aegislab.demo_showcase
~~~

The demo reuses identical synthetic submissions and appends a fresh evaluation/run. It exercises real authenticated routes, both allowed and blocked turns, separated reports, private artifact denial, original evidence verification and modified-copy rejection. It prints the report URL and writes metadata-only local-data/showcase_receipt.json plus exports in local-data/exports. Supabase round trips can make this take several minutes; no progress delays are inserted.

## Independent verification

~~~powershell
uv run --locked python -m aegislab.evidence local-data/exports/original.json --public-key local-data/exports/verification-key.pem
uv run --locked python -m aegislab.evidence local-data/exports/modified.json --public-key local-data/exports/verification-key.pem
~~~

Expected: original PASS / exit 0; modified FAIL / exit 1. Pin a public key and retain checkpoints independently; downloading a key from the same server is convenient for demonstration and is not independent trust establishment. Optionally pass --expected-run RUN_UUID. Raw prompts, defense terms, model responses and credentials are omitted from evidence; content digests and aggregate outcomes remain visible to the creating evaluator.

## Checks

~~~powershell
uv run --locked ruff check .
uv run --locked pytest
# Optional direct schema/migration and rollback-only immutability tests:
$env:AEGISLAB_RUN_DB_TESTS='1'
uv run --locked pytest -m integration -v
Remove-Item Env:AEGISLAB_RUN_DB_TESTS
~~~

The configured read-only DB connection test runs automatically. A failed configured connection fails the suite; opt-in schema checks are skipped unless enabled. Agent subprocesses in this environment cannot open PostgreSQL sockets, while the user-started backend can. Live HTTP checks exercise that backend; they do not replace direct-driver tests. See docs/PROGRESS.md for actual outcomes and limitations.

All Python work uses uv; dependency changes use uv add / uv add --dev. Preserve uv.lock and use uv sync --locked. If cache permissions require it, set $env:UV_CACHE_DIR = '.cache/uv'.

## Recording, scope and deployment preparation

- [Exact recording steps and 2–3 minute narration](docs/RECORDING_SHOWCASE.md)
- [Implemented/tested/planned matrix and trust model](docs/SHOWCASE_SCOPE.md)
- [Render/Vercel preparation](docs/DEPLOYMENT.md); no external deployment performed
- [Submission format and ownership rules](docs/PHASE_2_FORMAT.md)
- [Actual progress and historical checkpoints](docs/PROGRESS.md)

Older phase guides remain historical. Latest authorization replaced phase stops with one integrated web showcase and deferred Docker. Existing Docker files describe an optional older controller setup and are not needed or verified for this showcase. No benchmark or universal security claim is made.
