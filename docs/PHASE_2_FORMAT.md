# Phase 2 submission and authorization contract

## Accepted documents

Every document is JSON with exactly four fields: schema_version (integer 1), kind, name and config. Names contain 1–64 lowercase ASCII letters, digits or hyphens. Documents are inert data. No uploaded Python, commands, paths, URLs, model weights or arbitrary files are executed or fetched.

| Participant | Allowed kind | Exact config |
| --- | --- | --- |
| Red | attack | prompts: 1–8 strings, each 1–1000 characters |
| Blue | defense | blocked_terms: 1–32 strings, each 1–80 characters |
| Client | model | adapter: mock-v1; response: 1–2000 characters |
| Evaluator | policy | max_turns: 1–8; timeout_seconds: 1–60; max_message_bytes: 128–8192; all integers |

See fixtures/red-v1.json, red-v2.json, blue-v1.json, model-v1.json and policy-v1.json. These contain synthetic content only. The mock model is a specification in this phase; no model is executed.

Extra fields, duplicate JSON keys, non-finite numbers, booleans used as integers, NUL characters and unsupported kinds are rejected. Documents are limited to 16 KiB. The encoded HTTP request limit is 64 KiB so HTML URL-encoded forms can carry these documents. API bodies use application/json; HTML forms use application/x-www-form-urlencoded. There is no multipart upload interface.

Canonical content uses Python JSON serialization: sorted keys, separators comma/colon with no extra whitespace, ensure_ascii=False, allow_nan=False, then UTF-8. SHA-256 hashes those exact bytes. No Unicode normalization is performed, and this is not a claim of RFC 8785 compliance. Reformatting equivalent supported JSON does not create another version. A change to validated content does.

## Storage and version locking

A logical submission is identified by owner, kind and name. Each distinct canonical document receives a UUID, increasing version number and digest. Repeating an identical document returns the existing version. Version creation locks the logical submission row within a transaction to serialize concurrent appends.

Database triggers reject UPDATE, DELETE and TRUNCATE on submissions, submission_versions and evaluation_locks. Version digest constraints are also checked in PostgreSQL. A privileged database administrator can change triggers, schema or storage; that administrator remains trusted. Participants have no database credentials, and the controller uses a trusted database account. RLS is enabled without participant policies, but application authorization is the participant boundary in this prototype; the controller account may bypass RLS as the owner.

An evaluator creates an evaluation with exactly red_version_id, blue_version_id, model_version_id and policy_version_id. All must exist and have the right kind. The policy must belong to the creating evaluator. Foreign keys reference immutable versions. New submissions cannot repoint an existing lock. The stored evaluation is LOCKED, not executed. No success outcome, worker lifecycle or signed evidence is implied.

## Visibility policy

| Action | Red / Blue / Client | Evaluator |
| --- | --- | --- |
| Create artifact | Own role's kind | Own policy |
| List versions | Own metadata only | Own metadata only |
| Retrieve full version document | Owner only | Owner only |
| Coordination references | Denied | Submitted version IDs, owner/name/kind, version and digest; no document/config |
| Create evaluation lock | Denied | Allowed with valid references and own policy |
| View evaluation | Only if one of its submitted versions participates; shows own references only | Only evaluations created by that evaluator; shows all four metadata references |

Sharing an evaluation does not authorize another participant's private document. Unauthorized and unknown version IDs both return 404. The UI access-attempt form performs the same owner-scoped query and reports the observed outcome. It is an application authorization check, not a container storage test. Listings are bounded: 100 own versions, 200 coordination references and 30 evaluations per view.

## Authentication and request protection

Four synthetic demo accounts are created by uv run --locked python -m aegislab.demo_setup. Passwords are random and stored only in the ignored local-data/demo_accounts.json for private demo use. PostgreSQL stores salted PBKDF2-HMAC-SHA256 hashes with 600,000 iterations. No self-registration, password-reset, MFA or external identity provider is implemented.

Successful sign-in creates an opaque random 12-hour session. Only its SHA-256 digest is stored in PostgreSQL. The cookie is HttpOnly, SameSite=Strict and scoped to /. It deliberately lacks Secure for loopback HTTP development; do not use this configuration as a public deployment. Use localhost consistently during the demo so cookies and origin checks match.

State-changing authenticated requests require a per-session CSRF token. HTML forms include it in a hidden field. API clients obtain it from POST /api/auth/login or GET /api/auth/me, then send X-CSRF-Token. Cross-origin writes are rejected. Referrer-Policy=same-origin is used so normal HTML form POSTs retain their real Origin while cross-origin referrers are withheld. Login failures use a small in-memory per-client/username throttle; it resets on restart and is not a production distributed rate limiter. Session expiry and logout are enforced by the database-backed session lookup.

DB errors are sanitized. Private content, passwords, raw connection strings and session tokens are not written to application logs or demo output. Local machine, controller, database administrators and the private credentials file remain trusted. This authentication implementation has not been independently audited.

Sources: [OWASP password-storage guidance](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [PostgreSQL trigger semantics](https://www.postgresql.org/docs/17/trigger-definition.html).

## API summary

| Method / endpoint | Access |
| --- | --- |
| POST /api/auth/login | Username/password; creates cookie session |
| GET /api/auth/me | Authenticated actor and CSRF token |
| POST /api/auth/logout | Session plus CSRF; revokes current session |
| GET /api/submissions | Own version metadata |
| POST /api/submissions | Valid document, role and CSRF; stores/reuses version |
| GET /api/submissions/{version_id} | Full document, owner only |
| GET /api/evaluation-references | Evaluator metadata only |
| GET /api/evaluations | Authorized evaluation locks |
| POST /api/evaluations | Evaluator plus CSRF and four version IDs |
| GET /api/evaluations/{evaluation_id} | Authorized references, filtered by role |

There are no mutation or deletion endpoints for stored versions or evaluation locks. Role-specific evaluation reference filtering is implemented; complete evaluation reports remain Phase 5.
