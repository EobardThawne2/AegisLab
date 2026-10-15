CREATE TABLE aegislab.foundation_metadata (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    project_name text NOT NULL CHECK (project_name = 'AegisLab'),
    created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE aegislab.foundation_metadata ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON aegislab.foundation_metadata FROM PUBLIC;
INSERT INTO aegislab.foundation_metadata (singleton, project_name)
VALUES (true, 'AegisLab');
