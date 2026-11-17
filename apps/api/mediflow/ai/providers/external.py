"""
Optional Experimental External AI Provider Adapters (Gemini & Grok).

CRITICAL SECURITY INVARIANTS (SEC-014):
- Disabled by default; MEDIFLOW core functionality NEVER depends on these adapters.
- Only callable through ProviderRouter + PrivacyPolicyGuard with synthetic data.
- Gracefully handles missing API keys, HTTP 429 quota exhaustion, and timeouts.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from mediflow.ai.providers.base import (
    AIProviderError,
    EmbeddingResponse,
    GenerationRequest,
    GenerationResponse,
    ProviderHealth,
    ProviderQuotaError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class GeminiProvider:
    """Optional experimental Google Gemini REST adapter (synthetic experiments only)."""

    name: str = "gemini"
    is_local: bool = False

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str = "gemini-2.0-flash-exp",
        enabled: bool = False,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.default_model = default_model
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.enabled or not self._api_key:
            raise ProviderUnavailableError("Gemini provider is disabled or missing API key.")

        model = request.model or self.default_model
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        gen_cfg: dict[str, Any] = {
            "temperature": request.temperature,
            "maxOutputTokens": request.max_tokens,
        }
        if request.expect_json:
            gen_cfg["responseMimeType"] = "application/json"

        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": request.system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": request.user_prompt}]}],
            "generationConfig": gen_cfg,
        }

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                transport=self._transport,
            ) as client:
                resp = await client.post(
                    url,
                    headers={"x-goog-api-key": self._api_key},
                    json=body,
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Gemini request timed out.") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Gemini API unreachable.") from exc

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        if resp.status_code == 429:
            raise ProviderQuotaError("Gemini free-tier quota exceeded (HTTP 429).")
        if resp.status_code >= 400:
            raise AIProviderError(f"Gemini returned HTTP {resp.status_code}.")

        data = resp.json()
        candidates = data.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        content = "".join(str(p.get("text", "")) for p in parts)
        usage = data.get("usageMetadata", {})
        return GenerationResponse(
            content=content,
            provider=self.name,
            model=model,
            latency_ms=latency_ms,
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
        )

    async def embed(
        self, texts: list[str], *, model: str | None = None
    ) -> EmbeddingResponse:
        raise ProviderUnavailableError(
            "External embeddings are disabled; use local Ollama embeddings."
        )

    async def health_check(self, *, timeout_seconds: float = 0.5) -> ProviderHealth:
        configured = self.enabled and bool(self._api_key)
        return ProviderHealth(
            provider=self.name,
            is_local=False,
            available=configured,
            default_model=self.default_model,
            detail=(
                "Configured for synthetic-only experiments."
                if configured
                else "Disabled by default (local-first privacy mode)."
            ),
        )


class GrokProvider:
    """Optional experimental xAI Grok REST adapter (synthetic experiments only)."""

    name: str = "grok"
    is_local: bool = False

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str = "grok-beta",
        enabled: bool = False,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.default_model = default_model
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.enabled or not self._api_key:
            raise ProviderUnavailableError("Grok provider is disabled or missing API key.")

        model = request.model or self.default_model
        payload: dict[str, Any] = {
            "model": model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
        }
        if request.expect_json:
            payload["response_format"] = {"type": "json_object"}

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                transport=self._transport,
            ) as client:
                resp = await client.post(
                    "https://api.x.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Grok request timed out.") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("Grok API unreachable.") from exc

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        if resp.status_code == 429:
            raise ProviderQuotaError("Grok free-tier quota exceeded (HTTP 429).")
        if resp.status_code >= 400:
            raise AIProviderError(f"Grok returned HTTP {resp.status_code}.")

        data = resp.json()
        choices = data.get("choices", [])
        content = str(choices[0].get("message", {}).get("content", "")) if choices else ""
        usage = data.get("usage", {})
        return GenerationResponse(
            content=content,
            provider=self.name,
            model=str(data.get("model", model)),
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    async def embed(
        self, texts: list[str], *, model: str | None = None
    ) -> EmbeddingResponse:
        raise ProviderUnavailableError(
            "External embeddings are disabled; use local Ollama embeddings."
        )

    async def health_check(self, *, timeout_seconds: float = 0.5) -> ProviderHealth:
        configured = self.enabled and bool(self._api_key)
        return ProviderHealth(
            provider=self.name,
            is_local=False,
            available=configured,
            default_model=self.default_model,
            detail=(
                "Configured for synthetic-only experiments."
                if configured
                else "Disabled by default (local-first privacy mode)."
            ),
        )
