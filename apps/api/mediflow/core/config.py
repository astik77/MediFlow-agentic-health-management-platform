"""
MediFlow Core Configuration
Loads and validates all application settings from environment variables.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "MediFlow"
    app_version: str = "0.1.0"
    debug: bool = False

    # ---- API ----
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000"]

    # ---- Database ----
    database_url: str = (
        "postgresql+asyncpg://mediflow:mediflow_dev_password@localhost:5432/mediflow_db"
    )
    database_url_sync: str = (
        "postgresql+psycopg2://mediflow:mediflow_dev_password@localhost:5432/mediflow_db"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: int = 30

    # ---- Security ----
    secret_key: str = "CHANGE_ME_in_production_generate_a_secure_random_string"
    session_max_age_seconds: int = 86400
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    csrf_secret: str = "CHANGE_ME_csrf_secret"

    # ---- Password Hashing (Argon2id) ----
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4

    # ---- File Upload / Document Storage ----
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    allowed_extensions: list[str] = ["pdf", "jpg", "jpeg", "png", "webp", "tif", "tiff"]

    # ---- Document Intelligence & OCR (Phase 4) ----
    document_pipeline_version: str = "phase4-v1"
    max_document_pages: int = 50
    ocr_dpi: int = 200
    ocr_min_text_chars_per_page: int = 40
    document_chunk_max_chars: int = 1200
    document_chunk_overlap_chars: int = 150

    # ---- AI Providers ----
    ai_default_provider: Literal["ollama", "mock"] = "ollama"
    ai_structured_max_retries: int = 1
    ai_health_check_timeout_seconds: float = 0.5
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "qwen2.5:1.5b"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_recommended_models: list[str] = ["qwen2.5:1.5b", "llama3.2:1b", "qwen2.5:3b"]
    ollama_timeout_seconds: int = 120

    gemini_enabled: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-exp"

    grok_enabled: bool = False
    grok_api_key: str = ""
    grok_model: str = "grok-beta"

    # ---- External AI Safety ----
    allow_external_ai_for_real_data: bool = False
    external_ai_synthetic_only: bool = True

    # ---- Rate Limiting ----
    rate_limit_login_max: int = 5
    rate_limit_login_window_seconds: int = 300
    rate_limit_api_max: int = 100
    rate_limit_api_window_seconds: int = 60

    # ---- Logging ----
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("allowed_extensions", mode="before")
    @classmethod
    def parse_extensions(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
