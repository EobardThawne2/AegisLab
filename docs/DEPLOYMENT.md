# Prepared deployment configuration (not published)

The web showcase needs no Docker. The complete HTML/CSS site and FastAPI backend can run on one service with the existing Supabase PostgreSQL pooler. No hosting account, repository URL or public endpoint has been created.

## Shared configuration

Keep Python 3.12, pyproject.toml and uv.lock together. All dependency installation uses uv sync --locked --no-dev. Do not add requirements.txt or a second package workflow.

Set these privately in the chosen host:

| Variable | Value |
| --- | --- |
| DATABASE_URL | Existing Supabase pooler URI; password percent-encoded |
| DATABASE_POOLER_MODE | transaction, matching the configured pooler |
| DATABASE_SSLMODE | require, or verify-full with a trusted CA file |
| AEGISLAB_ENV | production (Secure session cookies) |
| AEGISLAB_PUBLIC_ORIGIN | Exact HTTPS origin, without a trailing slash |
| AEGISLAB_SIGNING_KEY | Base64-encoded 32-byte Ed25519 private key |
| AEGISLAB_AUTO_MIGRATE | true for the single-service showcase, or false after manually applying migrations |

Prepare the existing local signing key for private host configuration, outside the recording:

~~~powershell
uv run --locked python -m aegislab.deployment_key
~~~

Copy the value from ignored local-data/deployment-key.env to the host's secret settings. Never commit/upload that file or show it on video. Retain the same key across restarts; retain old public keys/checkpoints independently if keys are rotated. Production never generates a temporary key on the filesystem.

Synthetic account password hashes already reside in Supabase. Sign in with the existing privately retained credentials; do not ship local-data/demo_accounts.json. Fresh database setup is uv run --locked python -m aegislab.demo_setup from a trusted terminal with private configuration. No unauthenticated seed/admin endpoint exists.

## Render

render.yaml prepares a Python Web Service. The root .python-version selects 3.12; uv.lock makes uv available on Render. Build: uv sync --locked --no-dev. Start: uv run --locked --no-dev uvicorn aegislab.main:app --host 0.0.0.0 --port $PORT. The $PORT syntax is for Render's Linux shell, not a literal local PowerShell command.

Fill the three private sync:false settings before starting. Startup applies additive migrations under a transaction-scoped advisory lock when AUTO_MIGRATE is true. No schemas outside aegislab are modified. Readiness checks actual DB tables/checksums and signing-key availability. No local data directory is required in production.

References: [Render FastAPI](https://render.com/docs/deploy-fastapi), [Python and uv versions](https://render.com/docs/python-version), [Blueprint configuration](https://render.com/docs/blueprint-spec). Our commands intentionally use this project's uv workflow.

## Vercel

app.py exports the same FastAPI app; vercel.json requests a locked uv build and a 60-second function duration. Configure the shared production variables. Prefer applying migrations once from a trusted terminal and setting AUTO_MIGRATE=false to avoid repeated cold-start migration work. The existing DB stores accounts, sessions, runs and evidence; there are no background jobs or required local file writes.

Use the Python/FastAPI framework detection and pyproject.toml/uv.lock. Do not select a static-site-only deployment: the HTML is server-rendered and requires the backend. The function needs outbound Supabase pooler connectivity. Platform limits and plan availability apply. Configurations are prepared but no platform build/deployment has been executed or verified.

References: [Vercel FastAPI entrypoints, lifecycle and limits](https://vercel.com/docs/frameworks/backend/fastapi), [Python runtime/dependencies](https://vercel.com/docs/functions/runtimes/python).

## Prototype limits before sharing

Use synthetic data only. The controller/host/DB owner/signing key remain trusted. In-process login throttling is per instance and is not a distributed abuse-control system. Fixtures use simple term matching and a fixed mock response; no real model, untrusted code, isolated containers, gVisor or microVMs. Worker boundary checks remain UNVERIFIED. TLS require encrypts the connection; verify-full additionally validates server identity against a supplied CA. Verification proves signed records under the trusted key; it does not prove controller honesty or prevent rollback without independently retained checkpoints.
