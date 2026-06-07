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

    # LLM provider adapter (design §13). fake | anthropic | openai
    llm_provider: str = "fake"
    llm_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_model: str = "claude-opus-4-8"          # used when llm_provider=anthropic
    openai_llm_model: str = "gpt-4o"            # used when llm_provider=openai

    # Embedding provider adapter. fake | openai (Anthropic has no first-party
    # embeddings API; Voyage is the recommended pairing and is out of MVP scope).
    embedding_provider: str = "fake"
    embedding_model: str = "text-embedding-3-small"
    fake_embedding_dim: int = 64

    # TTS provider adapter (M7). fake | elevenlabs (stub) | ...
    tts_provider: str = "fake"
    tts_api_key: str = ""
    tts_sample_rate: int = 16000   # fake renderer output

    vector_db_url: str = ""

    # Chunking (design §11.1, §27). Token counts are heuristic in the MVP.
    chunk_target_tokens: int = 800
    chunk_overlap_tokens: int = 120

    # Auth (dev stub)
    jwt_secret: str = "dev-insecure-change-me"
    dev_bearer_token: str = "dev-token"
    admin_token: str = ""          # gates /api/admin/* ; empty disables admin endpoints

    # Cost estimation ($/1M tokens) for the configured LLM (design §20.3)
    llm_input_price_per_m: float = 5.0
    llm_output_price_per_m: float = 25.0

    # Job queue: inproc (default, no redis) | rq
    job_queue_backend: str = "inproc"


@lru_cache
def get_settings() -> Settings:
    return Settings()
