from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from aegislab import database, main
from aegislab.config import Settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "get_settings", lambda: Settings())
    with TestClient(main.app) as client:
        yield client


def test_live_does_not_require_database(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_readiness_fails_without_database(client):
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["database"]["status"] == "unverified"
    assert response.json()["ready"] is False
    assert response.json()["security_validation"] == "unverified"


def test_dashboard_marks_future_work_and_uses_no_javascript(client):
    response = client.get("/")
    assert response.status_code == 200
    for label in ["Private Submissions", "Version Locking", "Isolated Evaluation",
                  "Evidence", "Role-Specific Reports", "Security: UNVERIFIED", "Not configured"]:
        assert label in response.text
    assert "<script" not in response.text.lower()
    assert "script-src 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "no-store"
    assert client.get("/static/dashboard.css").status_code == 200


def test_database_error_is_not_reported_as_success_or_leaked(monkeypatch):
    secret = "private-password-do-not-leak"

    def failing_connect(_settings):
        raise psycopg.OperationalError(f"postgresql://user:{secret}@pooler.example/postgres")

    monkeypatch.setattr(database, "connect", failing_connect)
    result = database.status_snapshot(Settings(database_url="configured"))
    assert result["ready"] is False
    assert result["database"]["status"] == "error"
    assert secret not in str(result)
    assert "postgresql://" not in str(result)


def test_unconfigured_check_does_not_attempt_connection(monkeypatch):
    def unexpected_connect(_settings):
        raise AssertionError("Should not connect without a URI")

    monkeypatch.setattr(database, "connect", unexpected_connect)
    assert database.database_status(Settings())["status"] == "unverified"


@pytest.mark.parametrize("sslmode", ["disable", "allow", "prefer"])
def test_plaintext_database_modes_are_rejected(sslmode):
    with pytest.raises(ValueError):
        Settings(sslmode=sslmode).validate()


def test_unknown_pooler_mode_is_rejected():
    with pytest.raises(ValueError):
        Settings(pooler_mode="unknown").validate()


def test_verify_full_requires_a_ca():
    with pytest.raises(ValueError):
        Settings(sslmode="verify-full").validate()


def test_migration_command_fails_honestly_without_configuration(monkeypatch, capsys):
    from aegislab import migrate

    monkeypatch.setattr(migrate, "get_settings", lambda: Settings())
    assert migrate.main() == 1
    assert "set DATABASE_URL" in capsys.readouterr().out


def test_environment_overrides_file_and_reading_does_not_mutate_environment(monkeypatch, tmp_path):
    from aegislab import config

    monkeypatch.setattr(config, "ROOT", Path(tmp_path))
    (tmp_path / ".env").write_text("DATABASE_URL=from-file\n", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", "from-environment")
    assert config.get_settings().database_url == "from-environment"
    monkeypatch.delenv("DATABASE_URL")
    assert config.get_settings().database_url == "from-file"


def test_api_reference_also_uses_no_javascript(client):
    response = client.get("/api/docs")
    assert response.status_code == 200
    assert "<script" not in response.text.lower()
    assert "script-src 'none'" in response.headers["Content-Security-Policy"]
