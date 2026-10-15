"""Apply only AegisLab's versioned migrations. Run with uv run python -m aegislab.migrate."""
import sys

import psycopg

from aegislab.config import get_settings
from aegislab.database import bound_transaction, connect, migration_sources


def apply_migrations(settings) -> list[str]:
    applied = []
    with connect(settings) as connection:
        bound_transaction(connection)
        # Transaction-scoped lock works without retaining a pooled session.
        connection.execute("SELECT pg_advisory_xact_lock(91404001)")
        connection.execute("CREATE SCHEMA IF NOT EXISTS aegislab")
        connection.execute("REVOKE ALL ON SCHEMA aegislab FROM PUBLIC")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS aegislab.schema_migrations ("
            "version text PRIMARY KEY, checksum text NOT NULL, "
            "applied_at timestamptz NOT NULL DEFAULT now())"
        )
        connection.execute("ALTER TABLE aegislab.schema_migrations ENABLE ROW LEVEL SECURITY")
        connection.execute("REVOKE ALL ON aegislab.schema_migrations FROM PUBLIC")
        installed = connection.execute(
            "SELECT version, checksum FROM aegislab.schema_migrations"
        ).fetchall()
        recorded = {row["version"]: row["checksum"] for row in installed}
        sources = migration_sources()
        if set(recorded) - {version for version, _, _ in sources}:
            raise ValueError("Unknown migration; use the matching source version")
        for version, checksum, sql in sources:
            if version in recorded:
                if recorded[version] != checksum:
                    raise ValueError("An applied migration has changed; restore its original contents")
                continue
            connection.execute(sql, prepare=False)
            connection.execute(
                "INSERT INTO aegislab.schema_migrations (version, checksum) VALUES (%s, %s)",
                (version, checksum),
            )
            applied.append(version)
    return applied


def main() -> int:
    settings = get_settings()
    if not settings.database_url:
        print("Migration blocked: set DATABASE_URL in the local .env file.")
        return 1
    try:
        applied = apply_migrations(settings)
    except ValueError:
        print("Migration blocked. Check configuration and applied migration checksums.")
        return 1
    except psycopg.Error:
        print("Migration failed. Check pooler connectivity, credentials and schema permissions.")
        return 1
    print("Applied: " + ", ".join(applied) if applied else "Schema already current; no changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
