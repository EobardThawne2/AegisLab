"""Opt-in real PostgreSQL immutability checks; writes are rolled back."""
import os

import psycopg
import pytest

from aegislab.config import get_settings
from aegislab.database import bound_transaction, connect


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("AEGISLAB_RUN_DB_TESTS") != "1", reason="Direct schema mutation checks not requested")
def test_database_rejects_changes_to_stored_versions_and_locks():
    try:
        with connect(get_settings()) as connection:
            bound_transaction(connection)
            version = connection.execute(
                "SELECT v.id FROM aegislab.submission_versions v JOIN aegislab.submissions s ON s.id = v.submission_id "
                "JOIN aegislab.participants p ON p.id = s.owner_id WHERE p.synthetic = true LIMIT 1"
            ).fetchone()
            lock = connection.execute(
                "SELECT e.id FROM aegislab.evaluation_locks e JOIN aegislab.participants p ON p.id = e.created_by "
                "WHERE p.synthetic = true LIMIT 1"
            ).fetchone()
            if not version or not lock:
                pytest.skip("Run the synthetic Phase 2 HTTP demo before immutability checks")
            with pytest.raises(psycopg.errors.CheckViolation), connection.transaction():
                connection.execute("UPDATE aegislab.submission_versions SET canonical_document = canonical_document WHERE id = %s", (version["id"],))
            with pytest.raises(psycopg.errors.CheckViolation), connection.transaction():
                connection.execute("DELETE FROM aegislab.submission_versions WHERE id = %s", (version["id"],))
            with pytest.raises(psycopg.errors.CheckViolation), connection.transaction():
                connection.execute("UPDATE aegislab.evaluation_locks SET red_version_id = red_version_id WHERE id = %s", (lock["id"],))
            assert connection.execute("SELECT id FROM aegislab.submission_versions WHERE id = %s", (version["id"],)).fetchone()
            connection.rollback()
    except psycopg.Error:
        pass
    else:
        return
    # Fail outside the exception handler so pytest cannot print a chained driver error.
    pytest.fail("Real database immutability check could not complete; check connection, schema and permissions", pytrace=False)
