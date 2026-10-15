"""Small, bounded PostgreSQL operations compatible with Supabase poolers."""
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter

import psycopg
from psycopg.rows import dict_row

from aegislab.config import Settings

MIGRATIONS = Path(__file__).parent / "migrations"


def migration_sources() -> list[tuple[str, str, str]]:
    result = []
    for source in sorted(MIGRATIONS.glob("[0-9]*.sql")):
        sql = source.read_text(encoding="utf-8")
        result.append((source.stem, sha256(sql.encode("utf-8")).hexdigest(), sql))
    return result


def connect(settings: Settings) -> psycopg.Connection:
    settings.validate()
    if not settings.database_url:
        raise ValueError("DATABASE_URL is not configured")
    options = {
        "connect_timeout": 3,
        "prepare_threshold": None,  # No automatic prepared statements on transaction poolers.
        "sslmode": settings.sslmode,
        "row_factory": dict_row,
    }
    if settings.sslrootcert:
        options["sslrootcert"] = settings.sslrootcert
    return psycopg.connect(settings.database_url, **options)


def bound_transaction(connection: psycopg.Connection) -> None:
    # Transaction-local state: no reliance on pooled session state.
    connection.execute("SELECT set_config('statement_timeout', '5000', true)")
    connection.execute("SELECT set_config('lock_timeout', '3000', true)")


def database_status(settings: Settings) -> dict:
    result = {
        "status": "unverified",
        "label": "Not configured",
        "detail": "Add DATABASE_URL to the local .env file to check the Supabase pooler.",
        "pooler_mode": settings.pooler_mode,
        "schema_status": "unverified",
        "schema_label": "Not checked",
        "latency_ms": None,
        "postgres_version": None,
        "migration_versions": [],
    }
    if not settings.database_url:
        return result
    started = perf_counter()
    try:
        with connect(settings) as connection:
            bound_transaction(connection)
            row = connection.execute(
                "SELECT 1 AS probe, current_setting('server_version') AS version"
            ).fetchone()
            if row["probe"] != 1:
                raise RuntimeError("Unexpected database probe result")
            result.update(
                status="connected",
                label="Connected",
                detail="A live SELECT 1 completed through the configured PostgreSQL connection.",
                latency_ms=round((perf_counter() - started) * 1000),
                postgres_version=row["version"],
            )
            tables = connection.execute(
                "SELECT to_regclass('aegislab.schema_migrations') AS migrations, "
                "to_regclass('aegislab.foundation_metadata') AS metadata"
            ).fetchone()
            if not tables["migrations"] or not tables["metadata"]:
                result.update(schema_status="pending", schema_label="Migration required")
                return result
            installed = connection.execute(
                "SELECT version, checksum FROM aegislab.schema_migrations ORDER BY version"
            ).fetchall()
            result["migration_versions"] = [entry["version"] for entry in installed]
            recorded = {entry["version"]: entry["checksum"] for entry in installed}
            expected = {version: checksum for version, checksum, _ in migration_sources()}
            metadata = connection.execute(
                "SELECT project_name FROM aegislab.foundation_metadata WHERE singleton = true"
            ).fetchone()
            if any(version not in expected or expected[version] != checksum for version, checksum in recorded.items()):
                result.update(schema_status="mismatch", schema_label="Migration mismatch")
            elif set(recorded) != set(expected):
                result.update(schema_status="pending", schema_label="Migration required")
            else:
                objects = connection.execute(
                    "SELECT to_regclass('aegislab.participants') IS NOT NULL AND "
                    "to_regclass('aegislab.sessions') IS NOT NULL AND "
                    "to_regclass('aegislab.submissions') IS NOT NULL AND "
                    "to_regclass('aegislab.submission_versions') IS NOT NULL AND "
                    "to_regclass('aegislab.evaluation_locks') IS NOT NULL AND "
                    "to_regclass('aegislab.fixture_runs') IS NOT NULL AND "
                    "to_regclass('aegislab.evidence_verifications') IS NOT NULL AS ready"
                ).fetchone()
                if metadata and metadata["project_name"] == "AegisLab" and objects["ready"]:
                    result.update(schema_status="ready", schema_label="Current")
                else:
                    result.update(schema_status="error", schema_label="Required schema objects missing")
    except ValueError:
        result.update(status="error", label="Configuration error",
                      detail="Check the database URI, pooler mode and TLS settings in .env.")
    except (psycopg.Error, RuntimeError):
        if result["status"] == "connected":
            result.update(schema_status="error", schema_label="Schema check failed",
                          detail="Connected, but schema verification failed. Check database permissions.")
        else:
            result.update(status="error", label="Connection failed",
                          detail="The live database probe failed. Check credentials, network and pooler availability.")
    # Never return the URI, credentials, or raw database exception.
    return result


def status_snapshot(settings: Settings) -> dict:
    database = database_status(settings)
    return {
        "project": "AegisLab",
        "phase": "web-showcase",
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "backend": {"status": "running", "label": "Running", "version": "0.3.0"},
        "database": database,
        "ready": database["status"] == "connected" and database["schema_status"] == "ready",
        "evaluation": {"status": "fixture_execution_available", "model": "MOCK / mock-v1", "isolation": "unimplemented"},
        "security_validation": "unverified",
    }
