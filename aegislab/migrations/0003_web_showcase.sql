-- Web showcase: terminal fixture records only. No isolated worker claims.
CREATE TABLE aegislab.fixture_runs (
    id uuid PRIMARY KEY,
    evaluation_id uuid NOT NULL REFERENCES aegislab.evaluation_locks(id),
    created_by uuid NOT NULL REFERENCES aegislab.participants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    bundle jsonb NOT NULL,
    CHECK (bundle->>'format' = 'aegislab-evidence-v1'),
    CHECK (bundle->'manifest'->>'mode' = 'fixture_no_isolation'),
    CHECK (bundle->'manifest'->>'run_id' = id::text),
    CHECK (bundle->'manifest'->>'evaluation_id' = evaluation_id::text)
);
CREATE INDEX ON aegislab.fixture_runs(evaluation_id, created_at DESC);
CREATE TABLE aegislab.evidence_verifications (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES aegislab.fixture_runs(id),
    created_by uuid NOT NULL REFERENCES aegislab.participants(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    source text NOT NULL CHECK (source IN ('original', 'modified_copy')),
    bundle_digest text NOT NULL CHECK (length(bundle_digest) = 64),
    key_id text NOT NULL CHECK (length(key_id) = 64),
    valid boolean NOT NULL
);
CREATE INDEX ON aegislab.evidence_verifications(run_id, created_at DESC);
CREATE TRIGGER immutable_fixture_runs BEFORE UPDATE OR DELETE ON aegislab.fixture_runs
FOR EACH ROW EXECUTE FUNCTION aegislab.reject_artifact_change();
CREATE TRIGGER immutable_fixture_runs_truncate BEFORE TRUNCATE ON aegislab.fixture_runs
FOR EACH STATEMENT EXECUTE FUNCTION aegislab.reject_artifact_change();
CREATE TRIGGER immutable_verifications BEFORE UPDATE OR DELETE ON aegislab.evidence_verifications
FOR EACH ROW EXECUTE FUNCTION aegislab.reject_artifact_change();
CREATE TRIGGER immutable_verifications_truncate BEFORE TRUNCATE ON aegislab.evidence_verifications
FOR EACH STATEMENT EXECUTE FUNCTION aegislab.reject_artifact_change();
ALTER TABLE aegislab.fixture_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE aegislab.evidence_verifications ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON aegislab.fixture_runs, aegislab.evidence_verifications FROM PUBLIC;
