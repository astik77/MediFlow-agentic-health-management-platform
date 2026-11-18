"""
Local-First Ollama AI Provider Adapter.
Uses pure async httpx calls to Ollama's REST API (/api/chat, /api/embed, /api/tags).
Zero paid APIs, zero PyTorch overhead, tailored for CPU-constrained hosts (qwen2.5:1.5b).
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
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class OllamaProvider:
    """Async Ollama REST provider."""

    name: str = "ollama"
    is_local: bool = True

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        default_model: str = "qwen2.5:1.5b",
        embedding_model: str = "nomic-embed-text",
        timeout_seconds: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.embedding_model = embedding_model
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            transport=self._transport,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        model = request.model or self.default_model
        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }
        if request.expect_json:
            payload["format"] = "json"

        t0 = time.perf_counter()
        try:
            async with self._client(self.timeout_seconds) as client:
                resp = await client.post("/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Ollama request timed out after {self.timeout_seconds}s for model '{model}'."
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(
                f"Ollama server unreachable at {self.base_url}. "
                f"Ensure Ollama is running and '{model}' is pulled."
            ) from exc

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        if resp.status_code == 404:
            raise ProviderUnavailableError(
                f"Ollama model '{model}' not found. Run: ollama pull {model}"
            )
        if resp.status_code >= 400:
            raise AIProviderError(f"Ollama returned HTTP {resp.status_code}.")

        data = resp.json()
        content = str(data.get("message", {}).get("content", ""))
        return GenerationResponse(
            content=content,
            provider=self.name,
            model=str(data.get("model", model)),
            latency_ms=latency_ms,
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
            raw_metadata={"done_reason": data.get("done_reason")},
        )

    async def embed(
        self, texts: list[str], *, model: str | None = None
    ) -> EmbeddingResponse:
        emb_model = model or self.embedding_model
        t0 = time.perf_counter()
        try:
            async with self._client(self.timeout_seconds) as client:
                resp = await client.post(
                    "/api/embed",
                    json={"model": emb_model, "input": texts},
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Ollama embedding request timed out.") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(
                f"Ollama embedding server unreachable at {self.base_url}."
            ) from exc

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        if resp.status_code >= 400:
            raise AIProviderError(f"Ollama /api/embed returned HTTP {resp.status_code}.")

        data = resp.json()
        vectors: list[list[float]] = data.get("embeddings", [])
        dims = len(vectors[0]) if vectors else 0
        return EmbeddingResponse(
            embeddings=vectors,
            provider=self.name,
            model=str(data.get("model", emb_model)),
            dimensions=dims,
            latency_ms=latency_ms,
        )

    async def health_check(self, *, timeout_seconds: float = 0.5) -> ProviderHealth:
        try:
            async with self._client(timeout_seconds) as client:
                resp = await client.get("/api/tags")
            if resp.status_code != 200:
                return ProviderHealth(
                    provider=self.name,
                    is_local=True,
                    available=False,
                    default_model=self.default_model,
                    detail=f"Ollama returned HTTP {resp.status_code}",
                )
            models = [
                str(m.get("name", ""))
                for m in resp.json().get("models", [])
                if m.get("name")
            ]
            has_default = any(
                m == self.default_model or m.startswith(f"{self.default_model}:")
                for m in models
            )
            detail = (
                "Ollama reachable and default model ready."
                if has_default
                else f"Ollama reachable; pull default model with: ollama pull {self.default_model}"
            )
            return ProviderHealth(
                provider=self.name,
                is_local=True,
                available=True,
                default_model=self.default_model,
                installed_models=models,
                detail=detail,
            )
        except httpx.HTTPError:
            return ProviderHealth(
                provider=self.name,
                is_local=True,
                available=False,
                default_model=self.default_model,
                detail=(
                    f"Ollama not reachable at {self.base_url}. "
                    f"Install Ollama and run: ollama pull {self.default_model}"
                ),
            )
