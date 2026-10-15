# Deploy AegisLab to Render — beginner walkthrough

This guide walks you through publishing the existing FastAPI backend and HTML/CSS dashboard together on Render. Your database stays on Supabase. You do not need Docker, Vercel, a separate frontend service, or a new database for this route.

The configuration is prepared; a remote deployment has not been tested yet. Follow the checks at the end before sharing the link. The prototype uses a labeled mock model; worker isolation remains unimplemented and UNVERIFIED.

## 1. Open the project in PowerShell

1. Open PowerShell on your own PC.
2. Paste this command and press Enter:

~~~powershell
Set-Location "C:/Users/admin/Desktop/AegisLab"
~~~

3. Install/synchronize the project's exact locked dependencies:

~~~powershell
uv sync --locked
~~~

Expected: the command finishes without an error. The existing .venv is reused. You do not need to activate it manually; all Python commands below use uv run.

If uv reports a cache permission error, run this and try again:

~~~powershell
$env:UV_CACHE_DIR = '.cache/uv'
uv sync --locked
~~~

Keep your existing .env file. Do not replace its working Supabase connection with the placeholders from .env.example.

## 2. Prepare the signing key

Run:

~~~powershell
uv run --locked python -m aegislab.deployment_key
~~~

Expected: a message says the private deployment setting was written to local-data/deployment-key.env, or that the file already exists and was not overwritten. The command does not print the private key.

Outside your recording, open local-data/deployment-key.env in your text editor. It contains a line shaped like:

~~~text
AEGISLAB_SIGNING_KEY=<private value>
~~~

Later, you will copy ONLY the actual value after the first equals sign into Render. Keep any equals signs at the end of that value; they are part of the encoding. Do not add quotation marks or copy the example placeholder above.

Do not upload this file to GitHub. Keep the same key across deployments so existing evidence remains associated with the same signing identity.

## 3. Put the source on GitHub

### Create an empty private repository

1. Sign in to GitHub.
2. Click the + menu, then New repository.
3. Choose a repository name, such as AegisLab.
4. Select Private.
5. Leave Add a README, Add .gitignore and Choose a license unchecked; this project already has files.
6. Click Create repository.
7. Keep that page open. Copy the HTTPS repository address GitHub shows you. Use your actual address in the commands below.

### Commit the project from PowerShell

First, confirm the sensitive paths are ignored:

~~~powershell
git check-ignore .env .venv local-data/demo_accounts.json local-data/signing-key.pem local-data/deployment-key.env
git status --short
~~~

The check-ignore command should list the private paths. They must not appear as files being added in git status. The .env.example file is safe to include; your real .env is not.

Then run these commands one at a time:

~~~powershell
git add .
git commit -m "Prepare AegisLab web showcase"
git branch -M main
~~~

This repository is already initialized; do not create another repository inside it. Make sure pyproject.toml, uv.lock, .python-version, aegislab, fixtures and render.yaml are included in the commit.

If Git asks for your identity, configure it for this repository using your own details, then repeat the commit:

~~~powershell
git config user.name "YOUR NAME"
git config user.email "YOUR GITHUB EMAIL"
~~~

Connect the GitHub repository. Replace YOUR_REPOSITORY_HTTPS_URL with the address copied from GitHub:

~~~powershell
git remote add origin YOUR_REPOSITORY_HTTPS_URL
git push -u origin main
~~~

If Git says origin already exists, check it with git remote -v. If it is already the correct repository, skip remote add and just push. If it points elsewhere, stop and check which repository you intend to publish before changing it. Do not use a force push.

If Git opens a sign-in window, complete the normal GitHub sign-in. A GitHub website password is not used as a Git HTTPS password; use the browser/credential-manager flow.

If you see Permission denied for .git/index.lock, run the commands in your own normal PowerShell rather than the agent tool environment. The agent previously hit this filesystem restriction. Do not delete Git files or change security settings blindly. If the same error persists in your terminal, resolve the repository write-permission problem before continuing.

Refresh GitHub. You should see the source and uv.lock, with no .env, .venv or local-data folder.

## 4. Create a Render Web Service

1. Sign in at https://dashboard.render.com/.
2. Choose New, then Web Service.
3. Choose the option to connect a Git repository.
4. Connect your GitHub account if needed and grant access to the repository you just created.
5. Select that repository and continue to the service configuration screen.
6. Use the following settings:

| Render field | What to enter |
| --- | --- |
| Name | A service name of your choice; Render may require a unique name |
| Branch | main |
| Root Directory | Leave blank |
| Language / Runtime | Python 3; change it if Render detects Docker from the existing Dockerfile |
| Build Command | uv sync --locked --no-dev |
| Start Command | uv run --locked --no-dev uvicorn aegislab.main:app --host 0.0.0.0 --port $PORT |
| Health Check Path | /health/ready |

Choose an available instance type that suits your account. Review any displayed price before selecting a paid instance. If the health-check setting is not on this screen, set it under the service's Settings after creation.

Copy the start command into Render exactly as written. $PORT is expanded by Render's Linux shell; it is not a command to run in local PowerShell. Do not include --reload in the hosted start command.

The committed .python-version file selects Python 3.12. Leave PYTHON_VERSION unset unless you intentionally supply a supported, fully qualified 3.12 patch version. Do not accept an unrelated Python default.

This walkthrough uses manual Web Service setup. The included render.yaml is an alternative Blueprint configuration; you do not need to create a second service from it.

## 5. Add the environment variables

Find Environment Variables on the creation screen, or Environment on the service page. Add each name and value separately:

| Name | Value |
| --- | --- |
| UV_VERSION | 0.12.5 |
| AEGISLAB_ENV | production |
| AEGISLAB_AUTO_MIGRATE | true |
| DATABASE_POOLER_MODE | transaction |
| DATABASE_SSLMODE | require |
| DATABASE_URL | Your real, existing Supabase pooler connection string |
| AEGISLAB_SIGNING_KEY | The private value from local-data/deployment-key.env |
| AEGISLAB_PUBLIC_ORIGIN | The exact HTTPS origin Render assigns to this service, without a trailing slash; see step 6 |

For DATABASE_URL, privately open your local .env and copy the existing working value after DATABASE_URL=. Copy the entire connection string, including any query parameters. Do not paste the variable name, surrounding quotes or an example URI into the value field. Your connection uses the transaction pooler; keep the matching connection and mode.

For AEGISLAB_SIGNING_KEY, copy the complete value after the first equals sign from deployment-key.env. Do not generate a different key on every restart.

If Render has not assigned the service URL yet, add AEGISLAB_PUBLIC_ORIGIN immediately after the first deployment, as described below. Do not guess the URL from the service name.

You do not need Supabase anon/service-role API keys, a local PostgreSQL service, a persistent disk, or the local-data directory uploaded to Render for this application.

## 6. Deploy, then set the exact public origin

1. Click the create/deploy button for the Web Service.
2. Open the deployment logs.
3. Wait for the locked dependency build and application startup to finish.
4. Copy the actual HTTPS service URL displayed by Render.
5. Open the service's Environment section.
6. Add or correct AEGISLAB_PUBLIC_ORIGIN using that exact URL, with no trailing slash and no /login or other path.
7. Save the change using the option that redeploys/restarts the service. If necessary, use Manual Deploy to deploy the latest commit again.
8. Wait until the service is live, then open its URL.

For example, if the browser URL ends with /login, the origin is only the https://hostname portion. Use the actual hostname assigned to your service.

With AEGISLAB_AUTO_MIGRATE=true, trusted application startup applies missing additive migrations inside the aegislab schema and checks existing migration hashes. It does not reset accounts or delete earlier evaluations. The existing Supabase database already contains the synthetic demo accounts.

## 7. Check the deployed application

Do these checks on the Render URL:

1. Open the homepage and click Refresh checks. Expect Backend Running, PostgreSQL Connected and Schema Current. Worker security remains UNVERIFIED.
2. Open /health/ready on the same hostname. Expect HTTP 200 with ready=true. The response checks database/schema readiness and signing-key availability without exposing credentials.
3. Open /login. Sign in as demo-evaluator using its existing password from your private local-data/demo_accounts.json. Do not upload that file or show it in the recording.
4. Open Workspace. Existing version metadata/evaluations should be available because the deployment uses the same Supabase database.
5. Create a locked evaluation using red-showcase, blue-demo, mock-model and demo-policy. Run it. Expect 2 turns, 1 blocked decision and 1 mock-model call.
6. On the report, click Verify original. Expect PASS.
7. Click Test modified copy. Expect FAIL for that copy, with the original preserved.
8. Confirm that the five worker-isolation checks still say UNVERIFIED.

If the fixtures/accounts are missing because you intentionally configured a fresh Supabase database, run this from your trusted local terminal with that database configured privately in .env:

~~~powershell
uv run --locked python -m aegislab.demo_setup
~~~

That creates the schema/accounts, not the submission fixtures. Submit the fixtures through each participant's workspace afterward. For the existing working database, no reseeding is needed.

The current demo_showcase and check_running commands target localhost:8000. They do not automatically test your Render URL. Use the deployed browser checks above; do not interpret a successful localhost check as verification of the hosted service.

## 8. Updating the hosted prototype later

After making and checking changes locally:

~~~powershell
git add .
git commit -m "Describe your change"
git push
~~~

If automatic deployment is enabled, Render builds the new commit. Otherwise, use Manual Deploy on the service. Keep the existing environment variables and signing key. Your runs/accounts remain in Supabase.

Never edit previously applied SQL migrations. Add a new migration for future schema changes.

## Troubleshooting

| What you see | What to check |
| --- | --- |
| Render tries to build a Docker image | Select Python 3 for this Web Service. Docker is deferred for the showcase. |
| uv is not available | Confirm uv.lock is committed at the repository root and UV_VERSION is set. Render supports uv for projects with uv.lock. |
| Locked dependency build fails | Confirm pyproject.toml and uv.lock were committed together. Run uv sync --locked locally and inspect the actual build error; do not replace the workflow with another installer. |
| Python version mismatch | Confirm .python-version is in the repository root and requests 3.12. Remove a conflicting Render PYTHON_VERSION setting or set a supported full 3.12 version. |
| Port detection/startup failure | Check the start command includes --host 0.0.0.0 --port $PORT. |
| Database connection/readiness failure | Privately check DATABASE_URL, transaction-pooler mode, credentials, TLS, Supabase project availability and applicable network restrictions. Do not paste the connection string into a public issue. |
| Schema check fails | Confirm AUTO_MIGRATE=true and that the configured DB user can apply the aegislab migrations. Do not delete the schema or alter old migration files. |
| Signing key unavailable | Check the complete AEGISLAB_SIGNING_KEY value. Production requires the environment-provided key and does not create a temporary replacement. |
| Login/form returns Cross-origin requests are not allowed | Correct AEGISLAB_PUBLIC_ORIGIN to the exact HTTPS service origin, without a trailing slash/path, redeploy, then reload the form. |
| Session/CSRF error | Use the HTTPS URL, sign in again and reload the form. Production cookies are Secure. |
| An older bundle fails after changing keys | Verify it with its retained original public key. Server verification uses the current key. |

## What to keep private

- .env and the Supabase connection string.
- local-data/demo_accounts.json and the demo passwords.
- local-data/signing-key.pem and local-data/deployment-key.env.

The public verification key is safe to share. For independent verification, trust/pin that key separately and retain signed checkpoints independently.

## References

- [Render: deploy FastAPI](https://render.com/docs/deploy-fastapi)
- [Render: Python versions and uv support](https://render.com/docs/python-version)
- [Existing deployment notes, including the Vercel alternative](docs/DEPLOYMENT.md)
- [Recording walkthrough and narration](docs/RECORDING_SHOWCASE.md)

This guide only creates deployment instructions. No GitHub repository or Render service was created, no secrets were uploaded, and nothing was deployed by writing this file.
