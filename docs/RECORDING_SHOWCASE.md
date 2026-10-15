# AegisLab web showcase recording

Target: 2–3 minutes of selected screens aligned with slides 3, 4 and 7. This is a working provenance showcase with a clearly labeled mock model. Docker/isolated workers are deferred. Do not show .env, local-data/demo_accounts.json, signing-key.pem or deployment-key.env.

## Prepare off screen

Keep the existing local server running. If stopped:

~~~powershell
uv sync --locked
uv run --locked python -m aegislab.demo_setup
uv run --locked uvicorn aegislab.main:app --host 127.0.0.1 --port 8000 --reload
~~~

Local startup creates missing additive schema objects under an advisory lock; it does not modify old migrations or reset accounts/data. In another terminal:

~~~powershell
uv run --locked python -m aegislab.check_running
uv run --locked python -m aegislab.demo_showcase
~~~

Expect eight foundation checks and 23 showcase checks to pass (use the actual printed count if revised). Supabase round trips may take several minutes; let setup complete before recording. The last printed URL opens the new run. Metadata-only local-data/showcase_receipt.json contains run_id, evaluation_id and blue_version_id. The setup reuses immutable fixtures and appends a new run/lock. This is the scoped, non-destructive demo reset: rerun the command and use the newly printed IDs. No previous project data, private versions, keys or evidence are removed. Stop the server with Ctrl+C only after recording; resume with the same uvicorn command.

Privately sign in as demo-evaluator before recording using its existing generated password. Do not display the credentials file, terminal command line containing a password or browser password-manager suggestions. Sign out before switching roles. Use only synthetic fixture data.

## Capture these actions

1. Open http://localhost:8000 and click Refresh checks. Show Backend Running, PostgreSQL Connected and Schema Current, with a new check timestamp. Keep the explicit worker-isolation limitation visible. Expected: real server-side database query; no green security badges.
2. Open Workspace as Evaluator. Show four fixed-version selectors/digests. Select Red red-showcase v1, Blue blue-demo v1, Client mock-model v1 and your demo-policy v1; click Lock evaluation versions. Expected: a new evaluation ID and four immutable references.
3. Click Run bounded fixture evaluation. The browser navigates while the real request completes; no fabricated progress bar. Expected: completed run, 2 turns, 1 blocked, 1 mock call and the MOCK MODEL / Isolation UNVERIFIED labels.
4. Scroll through Validation matrix and Evaluation timeline. Expected: fixture bounds PASS; all five unexecuted worker tests UNVERIFIED; seven actual ordered events, including allowed/blocked Blue decisions and a mock response digest.
5. Click Verify original. Expected: Original PASS with a recorded verification UUID and bundle digest. Click Test modified copy. Expected: Modified copy FAIL; original record is retained. Click Export original if desired; it downloads JSON without raw prompts/policies/model responses.
6. Show offline verification in the second terminal using the pre-exported demo files:

~~~powershell
uv run --locked python -m aegislab.evidence local-data/exports/original.json --public-key local-data/exports/verification-key.pem
uv run --locked python -m aegislab.evidence local-data/exports/modified.json --public-key local-data/exports/verification-key.pem
~~~

Expected: PASS / exit 0 followed by FAIL / exit 1. That second exit code is the intentional tampering detection. These files match the CLI-prepared run; for a newly clicked browser run, use its downloaded original/modified files with the downloaded public key instead. Pin the public key separately for independent trust.

7. Off screen, sign out and sign in as demo-red. Open the same /workspace/runs/RUN_ID URL. Expected: Red-only artifact reference plus aggregate feedback, no Blue/model/policy references, full timeline or export controls. In Workspace, paste the synthetic blue_version_id into Try a version ID and attempt retrieval. Expected: Observed HTTP 404. Describe this as application-level private artifact denial, not container storage isolation.
8. End on the evaluator's report or mission control. Keep original/modified verification records visible for the final shot.

## Narration (about 2–3 minutes with pauses)

“AegisLab connects AI safety evaluation results to the exact inputs, policies and evidence behind them. This early web showcase uses Python, FastAPI and Supabase PostgreSQL, with an HTML and CSS interface. The model is explicitly a deterministic mock.

The dashboard checks the running backend and database. These connected indicators come from actual requests and database queries. They are not security certifications.

Each participant signs in to a role. Red submits attack fixtures, Blue submits defense rules, the Client supplies a mock-model configuration and the Evaluator supplies an execution policy. Documents are validated and assigned immutable versions with content digests. This evaluation locks those four specific versions. Later submissions do not replace the versions it references.

I can now run the bounded fixture evaluation. The first prompt is allowed through the Blue fixture and receives a mock response. The second is blocked. The resulting report shows two turns, one blocked decision and one mock-model call. Its timeline records the actual ordered interactions without exposing the private message contents.

This version does not provision isolated workers. The matrix keeps storage isolation, unauthorized networking, fresh worker state, worker termination and cleanup visibly unverified. We report only boundaries that were actually exercised.

The evidence bundle contains a hash-linked event chain and a signed final checkpoint. The original verifies against the public key. Testing a separate modified copy fails verification, while preserving the original. The same format can also be checked offline using a separately trusted public key and expected run identity. Independently retaining checkpoints matters because a hash chain alone does not stop history replacement.

Finally, the Red report contains only its authorized reference and aggregate feedback. Attempting to retrieve the known Blue artifact is denied. That demonstrates application authorization in the tested path.

This prototype demonstrates private version locking, bounded mock evaluation and verifiable reporting. Container isolation and real model adapters are future work.”

## Failure recovery and ready state

If readiness fails, keep the error on screen only when explaining it; check .env privately and run uv run --locked python -m aegislab.demo_setup from the trusted host terminal. Never mark blocked checks green. If signing is unavailable, check the ignored local key or production secret configuration; do not replace a key during a recording. If a form reports an expired session or CSRF error, sign in again and reload the form.

Leave the server running and retain .env, local-data keys/credentials, uv.lock and the Supabase aegislab schema. No external deployment is required. Screenshots in docs/screenshots/showcase-evidence.png show actual verification results; they contain synthetic IDs/digests only.
