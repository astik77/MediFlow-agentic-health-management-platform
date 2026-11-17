"""
Base AI Provider Protocol, Data Types, and Typed Exception Hierarchy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class AIProviderError(Exception):
    """Base error for all AI provider failures."""

    error_code: str = "ai_provider_error"


class ProviderUnavailableError(AIProviderError):
    """Raised when a local or remote AI backend cannot be reached or is disabled."""

    error_code = "provider_unavailable"


class ProviderTimeoutError(AIProviderError):
    """Raised when an AI provider exceeds its configured inference timeout."""

    error_code = "provider_timeout"


class ProviderQuotaError(AIProviderError):
    """Raised when an optional external provider returns HTTP 429 / quota exhaustion."""

    error_code = "provider_quota_exceeded"


class ExternalAIBlockedError(AIProviderError):
    """Raised by SEC-014 Privacy Firewall when real patient data targets an external API."""

    error_code = "external_ai_blocked_privacy"


@dataclass(slots=True)
class GenerationRequest:
    """Provider-agnostic generation request payload."""

    system_prompt: str
    user_prompt: str
    model: str | None = None
    temperature: float = 0.1
    max_tokens: int = 1024
    expect_json: bool = False
    json_schema: dict[str, Any] | None = None


@dataclass(slots=True)
class GenerationResponse:
    """Normalized response returned by any AIProvider."""

    content: str
    provider: str
    model: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EmbeddingResponse:
    """Normalized embedding vectors returned by an AIProvider."""

    embeddings: list[list[float]]
    provider: str
    model: str
    dimensions: int
    latency_ms: float


@dataclass(slots=True)
class ProviderHealth:
    """Health telemetry for an AI provider."""

    provider: str
    is_local: bool
    available: bool
    default_model: str
    installed_models: list[str] = field(default_factory=list)
    detail: str | None = None


class AIProvider(Protocol):
    """Uniform async interface implemented by local and optional external AI adapters."""

    name: str
    is_local: bool
    default_model: str

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Run chat/text generation and return normalized response."""
        ...

    async def embed(self, texts: list[str], *, model: str | None = None) -> EmbeddingResponse:
        """Generate dense embedding vectors for a batch of texts."""
        ...

    async def health_check(self, *, timeout_seconds: float = 0.5) -> ProviderHealth:
        """Check whether the provider is reachable and report available models."""
        ...
