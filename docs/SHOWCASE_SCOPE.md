# Web showcase scope and trust model

Latest user direction supersedes the earlier six-phase stop points: integrate the prototype now, defer Docker, prepare for Render/Vercel. This checkpoint is a provenance demonstration using deterministic data fixtures, not the proposed secure worker infrastructure.

| Capability | Implementation | Actual validation |
| --- | --- | --- |
| FastAPI / Supabase pooler / additive schema | Implemented | Running backend: live SELECT 1 and all three migration hashes/tables |
| Four synthetic roles and private submissions | Implemented | Authenticated HTTP owner access/denial and browser forms |
| Canonical digests, immutable versions and locks | Implemented | HTTP resubmission/new-version/preserved-lock tests; direct DB mutation tests remain unverified in agent sandbox |
| Bounded Red/Blue/mock-model evaluation | Implemented, trusted controller-side fixture interpretation | Live run: two turns, one blocked decision, one mock response; tests cover policy/message/deadline failures |
| Run timeline and role-specific reports | Implemented | Real stored events and HTTP role filtering; browser evaluator report |
| Ed25519-signed evidence and export | Implemented | Real signature and chain verification against configured key |
| Modified-copy detection | Implemented | Changed event copy rejected; unit tests also cover reordering/deletion/truncation/bad links/bad signatures/rechaining |
| Independent offline verifier | Implemented | CLI verifies original and rejects modified export when run with a trusted public key |
| Repeatable demo / logical reset | Implemented | Reuses synthetic documents; appends a new evaluation/run; no history or existing data deleted |
| HTML/CSS dashboard | Implemented | Browser checked; no JavaScript, fake progress or simulated worker lifecycle |
| Render / Vercel configuration | Prepared | Source configuration only; remote build, runtime and public deployment unverified |
| Separate workers / read-only roots / caps / deny-default networks | Deferred | UNVERIFIED, no workers in this showcase |
| Cross-team worker storage, unauthorized networking, session marker, worker termination/cleanup | Deferred | Five matrix rows remain UNVERIFIED; no marker freshness claim |
| gVisor, microVMs, CI, RAG, agents, multimodal | Planned | Outside prototype |

## Fixture mechanism

The controller loads the four locked documents from PostgreSQL in a trusted transaction. Each Red prompt is checked against byte/turn/deadline limits, then Blue performs case-insensitive substring matching. An allowed prompt receives the Client's fixed mock-v1 response; a blocked prompt produces a recorded blocked decision. No arbitrary commands, uploaded source or external model endpoints are accepted. At most eight prompts/turns and bounded messages are allowed by the documented format. Execution is synchronous and fast; the browser's normal navigation indicates loading. No background worker animation, sleeps or artificial delays are used. The fixture deadline is a cooperative application bound, not process termination.

The engine records terminal success or policy-limit failure, ordered events and aggregate counts. A database/signing failure returns an explicit error instead of an invented completed run. Connection loss before commit may leave no record; there is no durable job queue/recovery or worker cleanup claim.

## Visibility

| Viewer | Versions/documents | Run feedback | Evidence |
| --- | --- | --- | --- |
| Red | Own attack content and metadata only | Aggregate counts/status for evaluations using its version | No export/private timeline |
| Blue | Own defense content and metadata only | Same permitted aggregate feedback | No export/private timeline |
| Client | Own mock model content and metadata only | Same permitted aggregate feedback | No export/private timeline |
| Creating Evaluator | Own policy content; all locked version metadata | Redacted ordered events, outcome, validation results | Export and verification records |
| Unrelated participant | Own submissions only | No access to unrelated evaluation/run | No access |

The controller necessarily reads the locked documents to evaluate. Database service credentials, host/administrator access and signing keys are trusted. PostgreSQL RLS is enabled without participant policies; server authorization using the DB owner is the enforced application boundary. Evaluation membership does not grant another participant's document access. Reports/export exclude raw prompts, defense terms, model response and passwords. Digests, sizes and counts are still metadata and can reveal information, especially for guessable synthetic contents; do not load real sensitive artifacts into this early showcase.

## Evidence format

Canonical encoding is UTF-8 JSON with sorted keys, compact separators and finite numbers; it is this versioned Python format, not a claim of RFC 8785 interoperability. Event sequence numbers, previous digests and event digests form a SHA-256 chain. The signed final checkpoint binds format, run/evaluation IDs, event count/final digest, manifest/outcome/check digests and signing-key fingerprint. The manifest includes exact submission/policy references/digests, engine identifier/source digest and explicit fixture_no_isolation. Worker image digests are null because there are no images to attest.

The independent verifier requires a trusted Ed25519 public key; it never trusts an embedded key. Use --expected-run to bind the expected identity and retain the signed checkpoint independently to detect unwanted older-history substitution. Signatures do not prove the trusted controller reported truthfully, prevent host compromise, ensure evidence availability or stop a valid old bundle being presented without a retained expectation/checkpoint. Server verification uses the current configured key; after key rotation old bundles need their retained old public key. Local private keys are Git-ignored; Windows ACL protection depends on the private workspace. Production requires an environment-provided stable key and Secure cookies over the configured exact HTTPS origin.

## Checks and limitations

Run uv run --locked pytest for all tests. A configured direct DB connection failure is intentionally a failure; opt-in DB tests are not silently promoted to PASS. The agent sandbox blocks direct PostgreSQL sockets even though the existing user-started server can reach Supabase. HTTP verification checks actual server behavior but is not a direct SQL immutability/privilege audit. Current progress records exact outcomes. Distributed rate limiting, production key management, workload scheduling, external adapters and third-party security review are not implemented.
