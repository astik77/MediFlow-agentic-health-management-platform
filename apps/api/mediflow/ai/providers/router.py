"""
Provider Router & SEC-014 External AI Privacy Firewall.

Guarantees that real patient medical data is NEVER transmitted to external AI APIs
(Gemini, Grok) unless both explicit configuration AND synthetic-data policy allow it.
"""
from __future__ import annotations

from mediflow.ai.providers.base import (
    AIProvider,
    ExternalAIBlockedError,
    ProviderUnavailableError,
)
from mediflow.ai.providers.external import GeminiProvider, GrokProvider
from mediflow.ai.providers.mock import MockAIProvider
from mediflow.ai.providers.ollama import OllamaProvider
from mediflow.core.config import Settings, get_settings
from mediflow.core.logging import get_logger

logger = get_logger(__name__)


class PrivacyPolicyGuard:
    """
    SEC-014 enforcement gate evaluated before every AI provider dispatch.
    """

    @staticmethod
    def assert_provider_allowed(
        provider: AIProvider,
        *,
        settings: Settings,
        is_synthetic_data: bool = False,
    ) -> None:
        """
        Verify whether *provider* is permitted to process this request's data.
        - Local providers (Ollama, Mock) are always permitted.
        - External providers (Gemini, Grok) are hard-blocked for non-synthetic data
          under default configuration (allow_external_ai_for_real_data=False or
          external_ai_synthetic_only=True).
        """
        if provider.is_local:
            return

        if not is_synthetic_data:
            if settings.external_ai_synthetic_only or not settings.allow_external_ai_for_real_data:
                logger.warning(
                    "sec014_external_ai_blocked",
                    provider=provider.name,
                    is_synthetic_data=is_synthetic_data,
                    reason="real_patient_data_external_disallowed",
                )
                raise ExternalAIBlockedError(
                    f"External AI provider '{provider.name}' is blocked for real patient data "
                    "(SEC-014 privacy policy). Use local Ollama inference instead."
                )


class ProviderRouter:
    """Resolves configured AI providers and enforces the SEC-014 Privacy Firewall."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        override_providers: dict[str, AIProvider] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._providers: dict[str, AIProvider] = {
            "ollama": OllamaProvider(
                base_url=self.settings.ollama_base_url,
                default_model=self.settings.ollama_default_model,
                embedding_model=self.settings.ollama_embedding_model,
                timeout_seconds=float(self.settings.ollama_timeout_seconds),
            ),
            "gemini": GeminiProvider(
                api_key=self.settings.gemini_api_key,
                default_model=self.settings.gemini_model,
                enabled=self.settings.gemini_enabled,
            ),
            "grok": GrokProvider(
                api_key=self.settings.grok_api_key,
                default_model=self.settings.grok_model,
                enabled=self.settings.grok_enabled,
            ),
            "mock": MockAIProvider(),
        }
        if override_providers:
            self._providers.update(override_providers)

    def get_provider(
        self,
        provider_name: str | None = None,
        *,
        is_synthetic_data: bool = False,
    ) -> AIProvider:
        """
        Resolve provider by name (defaulting to local-first configured provider)
        and enforce SEC-014 privacy firewall before returning it.
        """
        target = (provider_name or self.settings.ai_default_provider).strip().lower()
        provider = self._providers.get(target)
        if provider is None:
            raise ProviderUnavailableError(f"Unknown AI provider '{target}'.")

        PrivacyPolicyGuard.assert_provider_allowed(
            provider,
            settings=self.settings,
            is_synthetic_data=is_synthetic_data,
        )
        return provider

    def get_raw_provider(self, provider_name: str) -> AIProvider:
        """Fetch provider solely for safe non-data metadata/health checks."""
        provider = self._providers.get(provider_name)
        if provider is None:
            raise ProviderUnavailableError(f"Unknown AI provider '{provider_name}'.")
        return provider
