"""
Environment-common settings loaded via pydantic-settings.

All secrets and environment-specific values are defined here.
Never import Django models or settings here — this module is pydantic-only.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvCommon(BaseSettings):
    """All environment-specific settings. Consumed by Django settings modules."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Django ─────────────────────────────────────────────────────────────────
    secret_key: str = Field(default="change-me-in-production")
    debug: bool = Field(default=False)
    allowed_hosts: str = Field(default="localhost,127.0.0.1")

    # ── Database ───────────────────────────────────────────────────────────────
    # PostgreSQL via Docker (see docker-compose.yml)
    # Port 5433 to avoid conflict with local PostgreSQL on 5432
    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5433/nexus_hr")

    # ── Redis ──────────────────────────────────────────────────────────────────
    # Uncomment redis service in docker-compose.yml to enable caching
    # redis_url: str = Field(default="redis://localhost:6379/0")

    # ── S3 / Storage ───────────────────────────────────────────────────────────
    # PRODUCTION ONLY — Uncomment when configuring S3 for production file storage
    # For local dev, use MinIO via docker-compose.yml or local filesystem
    # aws_access_key_id: str = Field(default="")
    # aws_secret_access_key: str = Field(default="")
    # aws_s3_bucket_name: str = Field(default="nexus-hr")
    # aws_s3_endpoint_url: str | None = Field(default=None)  # Set for MinIO in dev
    # aws_s3_region_name: str = Field(default="us-east-1")

    # ── JWT ────────────────────────────────────────────────────────────────────
    jwt_access_token_lifetime_minutes: int = Field(default=60)
    jwt_refresh_token_lifetime_days: int = Field(default=30)

    # ── Email ─────────────────────────────────────────────────────────────────
    # Dev defaults point to MailHog (see docker-compose.yml)
    # SMTP: localhost:1025, Web UI: http://localhost:8025
    email_host: str = Field(default="localhost")
    email_port: int = Field(default=1025)
    email_host_user: str = Field(default="")
    email_host_password: str = Field(default="")
    email_use_tls: bool = Field(default=False)
    email_from: str = Field(default="noreply@nexus-hr.local")

    # PRODUCTION ONLY — Configure real SMTP in production .env
    # email_host: str = Field(default="smtp.example.com")
    # email_port: int = Field(default=587)
    # email_use_tls: bool = Field(default=True)

    # ── Sentry ─────────────────────────────────────────────────────────────────
    # PRODUCTION ONLY — Error tracking and performance monitoring
    # Leave empty in development to disable Sentry
    # sentry_dsn: str = Field(default="")
    # sentry_environment: Literal["development", "staging", "production"] = Field(
    #     default="development"
    # )

    # ── Celery ─────────────────────────────────────────────────────────────────
    # Requires Redis (uncomment redis service in docker-compose.yml)
    # celery_broker_url: str = Field(default="redis://localhost:6379/1")
    # celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # ── Logging ─────────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")


@lru_cache
def get_env() -> EnvCommon:
    return EnvCommon()
