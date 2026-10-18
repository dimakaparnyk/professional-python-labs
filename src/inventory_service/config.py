"""Validated environment configuration; no embedded credentials."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///inventory.db"
    app_env: str = "development"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        result = cls(
            os.getenv("DATABASE_URL", "sqlite:///inventory.db"),
            os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")),
            os.getenv("LOG_LEVEL", "INFO").upper(),
        )
        if result.app_env not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test or production")
        if result.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Unsupported LOG_LEVEL")
        if not result.database_url.startswith("sqlite:///"):
            raise ValueError("This version supports SQLite database URLs")
        return result
