"""Environment-driven configuration (design §24.2).

All settings come from the environment / .env. Secrets never live in source
or the frontend (design §24.4).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"

    # Infra
    database_url: str = "postgresql://postgres:postgres@localhost:5432/podcast_synthesis"
    redis_url: str = "redis://localhost:6379/0"

    # Object storage
    object_storage_backend: str = "local"  # local | s3
    object_storage_bucket: str = "podcast-synthesis"
    object_storage_region: str = "us-east-1"
    local_storage_root: str = "./.storage"
    signed_url_expiry_seconds: int = 3600

    # Limits (design §22.3). 10 MB default per source for the MVP.
    max_source_bytes: int = 10 * 1024 * 1024

    # Provider adapters (later milestones)
    llm_provider: str = "fake"
    llm_api_key: str = ""
    tts_provider: str = "fake"
    tts_api_key: str = ""
    vector_db_url: str = ""

    # Auth (dev stub)
    jwt_secret: str = "dev-insecure-change-me"
    dev_bearer_token: str = "dev-token"

    # Job queue: inproc (default, no redis) | rq
    job_queue_backend: str = "inproc"


@lru_cache
def get_settings() -> Settings:
    return Settings()
