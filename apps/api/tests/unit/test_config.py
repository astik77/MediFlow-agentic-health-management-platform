"""
Unit tests for core configuration module.
Tests that Settings loads correctly and validates values.
"""
from __future__ import annotations

from mediflow.core.config import Settings, get_settings


class TestSettings:
    def test_default_settings_load(self) -> None:
        """Settings should load with default values without raising."""
        settings = Settings()
        assert settings.app_name == "MediFlow"
        assert settings.app_version == "0.1.0"
        assert settings.api_port == 8000
        assert settings.api_prefix == "/api/v1"

    def test_default_environment_is_development(self) -> None:
        settings = Settings()
        assert settings.app_env in ("development", "test")

    def test_cors_origins_default(self) -> None:
        settings = Settings()
        assert isinstance(settings.cors_origins, list)
        assert len(settings.cors_origins) >= 1

    def test_cors_origins_parsed_from_comma_string(self) -> None:
        settings = Settings(cors_origins="http://localhost:3000,http://localhost:3001")  # type: ignore[call-arg]
        assert "http://localhost:3000" in settings.cors_origins
        assert "http://localhost:3001" in settings.cors_origins

    def test_allowed_extensions_parsed_from_comma_string(self) -> None:
        settings = Settings(allowed_extensions="pdf,jpg,png")  # type: ignore[call-arg]
        assert "pdf" in settings.allowed_extensions
        assert "jpg" in settings.allowed_extensions
        assert "png" in settings.allowed_extensions

    def test_is_development_property(self) -> None:
        settings = Settings(app_env="development")  # type: ignore[call-arg]
        assert settings.is_development is True
        assert settings.is_production is False

    def test_is_production_property(self) -> None:
        settings = Settings(app_env="production")  # type: ignore[call-arg]
        assert settings.is_production is True
        assert settings.is_development is False

    def test_external_ai_disabled_by_default(self) -> None:
        settings = Settings()
        # Critical safety requirement: external AI must be off by default
        assert settings.allow_external_ai_for_real_data is False
        assert settings.external_ai_synthetic_only is True

    def test_gemini_disabled_by_default(self) -> None:
        settings = Settings()
        assert settings.gemini_enabled is False

    def test_grok_disabled_by_default(self) -> None:
        settings = Settings()
        assert settings.grok_enabled is False

    def test_get_settings_returns_singleton(self) -> None:
        """get_settings() must return the same cached instance."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_argon2_parameters_present(self) -> None:
        settings = Settings()
        assert settings.argon2_time_cost >= 2
        assert settings.argon2_memory_cost >= 32768
        assert settings.argon2_parallelism >= 1

    def test_max_upload_size_has_reasonable_default(self) -> None:
        settings = Settings()
        assert 1 <= settings.max_upload_size_mb <= 200
