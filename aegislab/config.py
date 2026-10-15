"""Read local configuration without exposing credentials in reports."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    database_url: str = ""
    pooler_mode: str = "session"
    sslmode: str = "require"
    sslrootcert: str = ""

    def validate(self) -> None:
        if self.pooler_mode not in {"session", "transaction"}:
            raise ValueError("DATABASE_POOLER_MODE must be session or transaction")
        if self.sslmode not in {"require", "verify-ca", "verify-full"}:
            raise ValueError("DATABASE_SSLMODE must require TLS")
        if self.sslmode in {"verify-ca", "verify-full"} and not self.sslrootcert:
            raise ValueError("A trusted CA certificate is required for this SSL mode")


def get_settings() -> Settings:
    # Environment variables take precedence; .env is re-read on page refresh.
    values = {**dotenv_values(ROOT / ".env", interpolate=False), **os.environ}
    return Settings(
        database_url=values.get("DATABASE_URL") or "",
        pooler_mode=values.get("DATABASE_POOLER_MODE") or "session",
        sslmode=values.get("DATABASE_SSLMODE") or "require",
        sslrootcert=values.get("DATABASE_SSLROOTCERT") or "",
    )
