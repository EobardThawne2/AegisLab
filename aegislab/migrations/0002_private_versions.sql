CREATE TABLE aegislab.participants (
    id uuid PRIMARY KEY,
    username text NOT NULL UNIQUE CHECK (username ~ '^[a-z0-9-]{3,40}$'),
    role text NOT NULL CHECK (role IN ('red', 'blue', 'client', 'evaluator')),
    password_hash text NOT NULL,
    synthetic boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE aegislab.sessions (
    token_hash text PRIMARY KEY CHECK (token_hash ~ '^[a-f0-9]{64}$'),
    participant_id uuid NOT NULL REFERENCES aegislab.participants(id),
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE aegislab.submissions (
    id uuid PRIMARY KEY,
    owner_id uuid NOT NULL REFERENCES aegislab.participants(id),
    kind text NOT NULL CHECK (kind IN ('attack', 'defense', 'model', 'policy')),
    name text NOT NULL CHECK (name ~ '^[a-z0-9-]{1,64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (owner_id, kind, name)
);
CREATE TABLE aegislab.submission_versions (
    id uuid PRIMARY KEY,
    submission_id uuid NOT NULL REFERENCES aegislab.submissions(id),
    version_number integer NOT NULL CHECK (version_number > 0),
    digest text NOT NULL CHECK (digest ~ '^[a-f0-9]{64}$'),
    canonical_document text NOT NULL CHECK (octet_length(canonical_document) <= 16384),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (submission_id, version_number),
    UNIQUE (submission_id, digest),
    CHECK (digest = encode(sha256(convert_to(canonical_document, 'UTF8')), 'hex'))
);
CREATE TABLE aegislab.evaluation_locks (
    id uuid PRIMARY KEY,
    created_by uuid NOT NULL REFERENCES aegislab.participants(id),
    red_version_id uuid NOT NULL REFERENCES aegislab.submission_versions(id),
    blue_version_id uuid NOT NULL REFERENCES aegislab.submission_versions(id),
    model_version_id uuid NOT NULL REFERENCES aegislab.submission_versions(id),
    policy_version_id uuid NOT NULL REFERENCES aegislab.submission_versions(id),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX sessions_expiry ON aegislab.sessions(expires_at);
CREATE INDEX version_history ON aegislab.submission_versions(submission_id, version_number DESC);
CREATE FUNCTION aegislab.reject_artifact_change() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, aegislab AS $$
BEGIN
    RAISE EXCEPTION 'Versioned artifacts and evaluation locks are immutable' USING ERRCODE = '23514';
END;
$$;
CREATE TRIGGER submissions_immutable BEFORE UPDATE OR DELETE ON aegislab.submissions
FOR EACH ROW EXECUTE FUNCTION aegislab.reject_artifact_change();
CREATE TRIGGER versions_immutable BEFORE UPDATE OR DELETE ON aegislab.submission_versions
FOR EACH ROW EXECUTE FUNCTION aegislab.reject_artifact_change();
CREATE TRIGGER locks_immutable BEFORE UPDATE OR DELETE ON aegislab.evaluation_locks
FOR EACH ROW EXECUTE FUNCTION aegislab.reject_artifact_change();
CREATE TRIGGER submissions_no_truncate BEFORE TRUNCATE ON aegislab.submissions
FOR EACH STATEMENT EXECUTE FUNCTION aegislab.reject_artifact_change();
CREATE TRIGGER versions_no_truncate BEFORE TRUNCATE ON aegislab.submission_versions
FOR EACH STATEMENT EXECUTE FUNCTION aegislab.reject_artifact_change();
CREATE TRIGGER locks_no_truncate BEFORE TRUNCATE ON aegislab.evaluation_locks
FOR EACH STATEMENT EXECUTE FUNCTION aegislab.reject_artifact_change();
ALTER TABLE aegislab.participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE aegislab.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE aegislab.submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE aegislab.submission_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE aegislab.evaluation_locks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA aegislab FROM PUBLIC;
REVOKE ALL ON FUNCTION aegislab.reject_artifact_change() FROM PUBLIC;
