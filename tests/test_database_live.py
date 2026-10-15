"""Real connection checks; schema/migration checks require explicit opt-in."""
import os

import pytest

from aegislab.config import get_settings
from aegislab.database import database_status
from aegislab.migrate import apply_migrations


@pytest.mark.integration
def test_live_pooler_connection():
    """Exercise the configured pooler on every normal test run, without database writes."""
    settings = get_settings()
    if not settings.database_url:
        pytest.skip("DATABASE_URL is not configured; live connectivity is unverified")
    status = database_status(settings)
    if status["status"] != "connected":
        # Report a safe constant message; no URI or raw driver exception in failures.
        pytest.fail(status["detail"], pytrace=False)


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("AEGISLAB_RUN_DB_TESTS") != "1", reason="Live DB test not requested")
def test_live_pooler_schema_and_repeat_migration():
    settings = get_settings()
    assert settings.database_url, "Configure DATABASE_URL privately before running live tests"
    status = database_status(settings)
    assert status["status"] == "connected", status["detail"]
    assert status["schema_status"] == "ready", "Run the initial migration first"
    assert apply_migrations(settings) == []
    assert database_status(settings)["schema_status"] == "ready"
