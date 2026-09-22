"""Runtime configuration, read from environment variables."""

import os
from dataclasses import dataclass

DEFAULT_DATABASE_URL = "sqlite:///./students.db"


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the settings the app needs at runtime."""

    database_url: str
    echo_sql: bool


def get_settings() -> Settings:
    """Build settings from the environment so nothing is hardcoded in the app."""
    return Settings(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        echo_sql=os.getenv("SQL_ECHO", "0").lower() in {"1", "true", "yes"},
    )
