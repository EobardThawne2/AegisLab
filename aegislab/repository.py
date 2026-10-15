"""PostgreSQL persistence. Private content queries always include the owner ID."""
import json
from uuid import UUID, uuid4

from aegislab.documents import ROLE_KIND, Problem, validate_document

VERSION_COLUMNS = """v.id, v.submission_id, v.version_number, v.digest, v.created_at,
    s.owner_id, s.kind, s.name, p.username AS owner_username, p.role AS owner_role"""
VERSION_FROM = """FROM aegislab.submission_versions v
    JOIN aegislab.submissions s ON s.id = v.submission_id
    JOIN aegislab.participants p ON p.id = s.owner_id"""


def public(row):
    return json.loads(json.dumps(dict(row), default=str)) if row else None


def valid_id(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise Problem(404, "Not found") from None


class Repository:
    def __init__(self, connection):
        self.connection = connection

    def participant(self, username):
        return self.connection.execute(
            "SELECT id, username, role, synthetic, password_hash FROM aegislab.participants WHERE username = %s",
            (username,),
        ).fetchone()

    def session_actor(self, hashed):
        row = self.connection.execute(
            "SELECT p.id, p.username, p.role, p.synthetic FROM aegislab.sessions s "
            "JOIN aegislab.participants p ON p.id = s.participant_id "
            "WHERE s.token_hash = %s AND s.expires_at > now()", (hashed,),
        ).fetchone()
        return public(row)

    def save_session(self, hashed, participant_id):
        self.connection.execute(
            "INSERT INTO aegislab.sessions (token_hash, participant_id, expires_at) "
            "VALUES (%s, %s, now() + interval '12 hours')", (hashed, participant_id),
        )

    def delete_session(self, hashed):
        self.connection.execute("DELETE FROM aegislab.sessions WHERE token_hash = %s", (hashed,))

    def list_versions(self, actor):
        rows = self.connection.execute(
            "SELECT " + VERSION_COLUMNS + " " + VERSION_FROM
            + " WHERE s.owner_id = %s ORDER BY v.created_at DESC, v.id LIMIT 100", (actor["id"],),
        ).fetchall()
        return [public(row) for row in rows]

    def version(self, actor, version_id):
        row = self.connection.execute(
            "SELECT " + VERSION_COLUMNS + ", v.canonical_document " + VERSION_FROM
            + " WHERE v.id = %s AND s.owner_id = %s", (valid_id(version_id), actor["id"]),
        ).fetchone()
        if not row:
            raise Problem(404, "Not found")
        result = public(row)
        result["document"] = json.loads(result.pop("canonical_document"))
        return result

    def submit(self, actor, document):
        canonical, digest = validate_document(document)
        if document["kind"] != ROLE_KIND[actor["role"]]:
            raise Problem(403, "Your role cannot submit this artifact kind")
        self.connection.execute(
            "INSERT INTO aegislab.submissions (id, owner_id, kind, name) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (owner_id, kind, name) DO NOTHING",
            (uuid4(), actor["id"], document["kind"], document["name"]),
        )
        parent = self.connection.execute(
            "SELECT id FROM aegislab.submissions WHERE owner_id = %s AND kind = %s AND name = %s FOR UPDATE",
            (actor["id"], document["kind"], document["name"]),
        ).fetchone()
        submission_id = parent["id"]
        existing = self.connection.execute(
            "SELECT id, canonical_document FROM aegislab.submission_versions WHERE submission_id = %s AND digest = %s",
            (submission_id, digest),
        ).fetchone()
        if existing:
            if existing["canonical_document"] != canonical:
                raise Problem(409, "Digest collision; submission rejected")
            result = self.version(actor, existing["id"])
            result["reused_existing_version"] = True
            return result
        number = self.connection.execute(
            "SELECT COALESCE(max(version_number), 0) + 1 AS next FROM aegislab.submission_versions WHERE submission_id = %s",
            (submission_id,),
        ).fetchone()["next"]
        version_id = uuid4()
        self.connection.execute(
            "INSERT INTO aegislab.submission_versions (id, submission_id, version_number, digest, canonical_document) "
            "VALUES (%s, %s, %s, %s, %s)", (version_id, submission_id, number, digest, canonical),
        )
        result = self.version(actor, version_id)
        result["reused_existing_version"] = False
        return result

    def references(self, actor):
        if actor["role"] != "evaluator":
            raise Problem(403, "Evaluator role required")
        rows = self.connection.execute(
            "SELECT " + VERSION_COLUMNS + " " + VERSION_FROM + " ORDER BY v.created_at DESC, v.id LIMIT 200"
        ).fetchall()
        # Explicit metadata projection. No canonical document or config is selected.
        return [public(row) for row in rows]

    def lock(self, actor, values):
        if actor["role"] != "evaluator":
            raise Problem(403, "Evaluator role required")
        mapping = {"red_version_id": "attack", "blue_version_id": "defense",
                   "model_version_id": "model", "policy_version_id": "policy"}
        if not isinstance(values, dict) or set(values) != set(mapping):
            raise Problem(422, "Exactly four fixed version references are required")
        ids = {key: valid_id(value) for key, value in values.items()}
        for key, kind in mapping.items():
            row = self.connection.execute(
                "SELECT s.kind, s.owner_id FROM aegislab.submission_versions v "
                "JOIN aegislab.submissions s ON s.id = v.submission_id WHERE v.id = %s", (ids[key],),
            ).fetchone()
            if not row or row["kind"] != kind:
                raise Problem(422, "One or more references do not match the required artifact kind")
            if kind == "policy" and str(row["owner_id"]) != actor["id"]:
                raise Problem(403, "Lock one of your own policy versions")
        evaluation_id = uuid4()
        self.connection.execute(
            "INSERT INTO aegislab.evaluation_locks "
            "(id, created_by, red_version_id, blue_version_id, model_version_id, policy_version_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (evaluation_id, actor["id"], ids["red_version_id"], ids["blue_version_id"],
             ids["model_version_id"], ids["policy_version_id"]),
        )
        return self.evaluation(actor, evaluation_id)

    def evaluation_rows(self, actor, evaluation_id=None):
        condition = ("(e.created_by = %s OR EXISTS (SELECT 1 FROM aegislab.submission_versions v "
                     "JOIN aegislab.submissions s ON s.id = v.submission_id WHERE s.owner_id = %s "
                     "AND v.id IN (e.red_version_id, e.blue_version_id, e.model_version_id, e.policy_version_id)))")
        parameters = [actor["id"], actor["id"]]
        if evaluation_id is not None:
            condition += " AND e.id = %s"
            parameters.append(valid_id(evaluation_id))
        return self.connection.execute(
            "SELECT e.* FROM aegislab.evaluation_locks e WHERE " + condition
            + " ORDER BY e.created_at DESC, e.id LIMIT 30", parameters,
        ).fetchall()

    def evaluation_views(self, actor, rows):
        if not rows:
            return []
        keys = ("red_version_id", "blue_version_id", "model_version_id", "policy_version_id")
        identifiers = list({str(row[key]) for row in rows for key in keys})
        references = self.connection.execute(
            "SELECT " + VERSION_COLUMNS + " " + VERSION_FROM + " WHERE v.id = ANY(%s::uuid[])",
            (identifiers,),
        ).fetchall()
        by_id = {str(reference["id"]): reference for reference in references}
        result = []
        for row in rows:
            evaluation = {"id": str(row["id"]), "status": "locked", "created_at": str(row["created_at"]),
                          "execution": "Bounded mock fixtures available; isolated workers deferred", "versions": {}}
            for key in keys:
                reference = by_id[str(row[key])]
                if str(row["created_by"]) == actor["id"] or str(reference["owner_id"]) == actor["id"]:
                    evaluation["versions"][key] = public(reference)
            result.append(evaluation)
        return result

    def evaluation(self, actor, evaluation_id):
        rows = self.evaluation_rows(actor, evaluation_id)
        if not rows:
            raise Problem(404, "Not found")
        return self.evaluation_views(actor, rows)[0]

    def list_evaluations(self, actor):
        return self.evaluation_views(actor, self.evaluation_rows(actor))
