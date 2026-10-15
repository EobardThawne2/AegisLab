"""Create only synthetic demo accounts; never print their passwords."""
import json
import os
import secrets
import sys
from uuid import NAMESPACE_URL, uuid5

import psycopg

from aegislab.config import ROOT, get_settings
from aegislab.database import bound_transaction, connect
from aegislab.documents import ROLE_KIND
from aegislab.migrate import apply_migrations
from aegislab.passwords import hash_password, verify_password

CREDENTIALS = ROOT / "local-data" / "demo_accounts.json"


def prepare_credentials():
    CREDENTIALS.parent.mkdir(parents=True, exist_ok=True)
    if not CREDENTIALS.exists():
        values = {role: {"username": "demo-" + role, "password": secrets.token_urlsafe(24)}
                  for role in ROLE_KIND}
        descriptor = os.open(CREDENTIALS, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(values, handle, indent=2)
    values = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
    if set(values) != set(ROLE_KIND) or any(
        values[role].get("username") != "demo-" + role
        or not isinstance(values[role].get("password"), str) or len(values[role]["password"]) < 24
        for role in ROLE_KIND
    ):
        raise ValueError("Invalid private demo credentials file")
    return values


def seed(settings, credentials):
    with connect(settings) as connection:
        bound_transaction(connection)
        connection.execute("SELECT pg_advisory_xact_lock(91404002)")
        for role, values in credentials.items():
            row = connection.execute(
                "SELECT role, synthetic, password_hash FROM aegislab.participants WHERE username = %s",
                (values["username"],),
            ).fetchone()
            if row:
                if row["role"] != role or not row["synthetic"] or not verify_password(values["password"], row["password_hash"]):
                    raise ValueError("Existing accounts do not match the private demo credentials; no passwords changed")
                continue
            connection.execute(
                "INSERT INTO aegislab.participants (id, username, role, password_hash, synthetic) VALUES (%s, %s, %s, %s, true)",
                (uuid5(NAMESPACE_URL, "aegislab-synthetic-" + role), values["username"], role,
                 hash_password(values["password"])),
            )


def main():
    try:
        credentials = prepare_credentials()
        settings = get_settings()
        applied = apply_migrations(settings)
        seed(settings, credentials)
    except (ValueError, OSError, psycopg.Error):
        print("Setup failed. Check pooler connectivity, migration permissions and the private demo credentials file.")
        print("Existing passwords and submissions were not reset. Credentials are never printed.")
        return 1
    print("Schema: " + (", ".join(applied) if applied else "already current"))
    print("Four synthetic demo accounts are ready: Red, Blue, Client, Evaluator.")
    print("Private credentials: local-data/demo_accounts.json (keep off screen and out of source control).")
    print("No submissions or evaluations have been fabricated. Submit fixtures through the authenticated API or workspace.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
