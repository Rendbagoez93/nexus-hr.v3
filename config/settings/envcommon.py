"""
Environment-common settings loaded via pydantic-settings.

This module implements environment values as swappable "building blocks":

- ``EnvCommon``      — fields and defaults shared by every environment.
- ``LocalEnv``       — development building block. Permissive defaults,
                        reads ``.env`` / ``.env.local``.
- ``ProductionEnv``  — production building block. No insecure defaults —
                        secrets with no safe default are declared without a
                        default value, so pydantic raises a ``ValidationError``
                        at startup if they're missing, instead of silently
                        falling back to a dev value. Reads ``.env.production``.

``get_env()`` picks the correct block based on the ``DJANGO_ENV`` variable —
the same variable `config/settings/__init__.py` uses to choose between
`local.py` and `production.py`. Both switches read the same variable, so the
Django settings module and the pydantic settings values always agree.

Never import Django models or settings here — this module is pydantic-only.
"""

import os
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_comma_separated(value: object) -> object:
    """Allow list fields (e.g. ALLOWED_HOSTS) to be written as "a,b,c" in a .env file."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class EnvCommon(BaseSettings):
    """Fields and defaults shared by every environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Django Core ──────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        default="django-insecure-change-me-in-production",
        description="Django secret key. Must be unique and unpredictable in production.",
    )
    DEBUG: bool = Field(default=False, description="Never True in production.")
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = Field(
        default=["localhost", "127.0.0.1"],
        description="Hosts/domains the Django site can serve.",
    )

    # ── Database — PostgreSQL via psycopg v3 ─────────────────────────────────
    DB_NAME: str = Field(default="nexus_hr", description="PostgreSQL database name.")
    DB_USER: str = Field(default="postgres", description="PostgreSQL role/user.")
    DB_PASSWORD: str = Field(default="postgres", description="PostgreSQL password.")
    DB_HOST: str = Field(default="localhost", description="PostgreSQL host.")
    DB_PORT: int = Field(default=5433, description="PostgreSQL port.")

    # ── Redis ──────────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Cache / session store.")

    # ── JWT ────────────────────────────────────────────────────────────────────
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES: int = Field(default=60)
    JWT_REFRESH_TOKEN_LIFETIME_DAYS: int = Field(default=30)

    # ── Email ─────────────────────────────────────────────────────────────────
    # Dev defaults point to MailHog (see docker-compose.yml)
    # SMTP: localhost:1025, Web UI: http://localhost:8025
    EMAIL_HOST: str = Field(default="localhost")
    EMAIL_PORT: int = Field(default=1025)
    EMAIL_HOST_USER: str = Field(default="")
    EMAIL_HOST_PASSWORD: str = Field(default="")
    EMAIL_USE_TLS: bool = Field(default=False)
    EMAIL_FROM: str = Field(default="noreply@nexus-hr.local")

    # ── Sentry ─────────────────────────────────────────────────────────────────
    # Leave SENTRY_DSN empty to disable Sentry (default for development).
    SENTRY_DSN: str = Field(default="")
    SENTRY_ENVIRONMENT: Literal["development", "staging", "production"] = Field(default="development")

    # ── Logging ─────────────────────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def _parse_allowed_hosts(cls, value: object) -> object:
        return _split_comma_separated(value)


class LocalEnv(EnvCommon):
    """Development building block — permissive defaults, safe to run with zero .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    DEBUG: bool = Field(default=True)


class ProductionEnv(EnvCommon):
    """Production building block — required secrets have no default and fail fast if unset."""

    model_config = SettingsConfigDict(
        env_file=".env.production",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    SECRET_KEY: str  # required — no insecure default in production
    DEBUG: bool = Field(default=False)
    ALLOWED_HOSTS: Annotated[list[str], NoDecode]  # required — must be explicit in production
    DB_PASSWORD: str  # required — no default DB password in production
    REDIS_URL: str  # required
    SENTRY_ENVIRONMENT: Literal["development", "staging", "production"] = Field(default="production")


@lru_cache
def get_env() -> EnvCommon:
    """Return the settings "building block" for the active environment.

    Reads DJANGO_ENV — the same variable `config/settings/__init__.py` uses
    to choose between `local.py` and `production.py` — so both switches
    always agree on which environment is active.
    """
    environment = os.environ.get("DJANGO_ENV", "local")
    if environment == "production":
        return ProductionEnv()
    return LocalEnv()
