"""
Deterministic In-Process Mock AI Provider.
Used for hermetic unit/API testing and offline evaluation without requiring Ollama.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable

from mediflow.ai.providers.base import (
    EmbeddingResponse,
    GenerationRequest,
    GenerationResponse,
    ProviderHealth,
)

_PATIENT_ID_RE = re.compile(r"Patient ID:\s*([0-9a-fA-F\-]{36})")
_TITLE_RE = re.compile(r"Document Title:\s*(.+)")


class MockAIProvider:
    """Deterministic local stub provider for automated test suites."""

    name: str = "mock"
    is_local: bool = True
    default_model: str = "mock-mediflow-v1"

    def __init__(
        self,
        *,
        responder: Callable[[GenerationRequest], str] | None = None,
        response_sequence: list[str] | None = None,
    ) -> None:
        self._responder = responder
        self._sequence = list(response_sequence) if response_sequence else []
        self.calls: list[GenerationRequest] = []

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.calls.append(request)
        if self._sequence:
            content = self._sequence.pop(0)
        elif self._responder is not None:
            content = self._responder(request)
        elif request.expect_json:
            pid_match = _PATIENT_ID_RE.search(request.user_prompt)
            pid = pid_match.group(1) if pid_match else "00000000-0000-0000-0000-000000000000"
            if "Longitudinal Health Summary Window:" in request.user_prompt:
                # Phase 8 7-Day Health Summary deterministic local AI response
                content = json.dumps(
                    {
                        "patient_id": pid,
                        "headline": "Personal Longitudinal Health Summary",
                        "summary_text": (
                            "Over the selected window, your confirmed observations, ongoing "
                            "symptoms, and uploaded records were reviewed. Any out-of-range "
                            "biomarkers or notable trends are highlighted below for discussion "
                            "with your healthcare provider."
                        ),
                        "highlights": [
                            "Confirmed longitudinal observations and active symptoms summarized.",
                            "Unconfirmed document candidates were excluded pending your review.",
                        ],
                        "questions_for_doctor": [
                            (
                                "Are any recent changes in my tracked biomarkers "
                                "clinically meaningful?"
                            ),
                            "Should I repeat any out-of-range lab measurements at my next visit?",
                        ],
                        "informational_disclaimer": (
                            "This longitudinal health summary is strictly informational and does "
                            "not constitute medical advice, diagnosis, or treatment."
                        ),
                    }
                )
            elif "Latest Patient Message:" in request.user_prompt:
                # Phase 6 AI Health Assistant deterministic response
                user_msg = request.user_prompt.split("Latest Patient Message:", 1)[1].strip()
                mentions_symptom = any(
                    k in user_msg.lower()
                    for k in (
                        "headache",
                        "fever",
                        "fatigue",
                        "cough",
                        "nausea",
                        "dizziness",
                        "pain",
                    )
                )
                content = json.dumps(
                    {
                        "patient_id": pid,
                        "reply": (
                            "Based on your recorded personal health history, I have reviewed "
                            "your active conditions, allergies, recent symptoms, and confirmed "
                            "observations to help answer your question."
                        ),
                        "clarifying_questions": (
                            [
                                "When did this symptom first start?",
                                "How would you rate its severity (mild, moderate, or severe)?",
                            ]
                            if mentions_symptom
                            else []
                        ),
                        "cited_record_ids": [],
                        "proposed_symptom": (
                            {
                                "name": "Headache"
                                if "headache" in user_msg.lower()
                                else "Reported Symptom",
                                "severity": "moderate",
                                "body_location": "head" if "headache" in user_msg.lower() else None,
                                "frequency": None,
                                "notes": "Proposed from health assistant conversation",
                            }
                            if mentions_symptom
                            else None
                        ),
                        "informational_disclaimer": (
                            "This response is strictly informational and is not medical advice, "
                            "a diagnosis, or a prescription."
                        ),
                    }
                )
            else:
                title_match = _TITLE_RE.search(request.user_prompt)
                title = title_match.group(1).strip() if title_match else "Medical Document"
                content = json.dumps(
                    {
                        "patient_id": pid,
                        "plain_language_summary": (
                            f"This summary explains the extracted content of '{title}' "
                            "in plain language for your personal review."
                        ),
                        "key_findings": [
                            "Document text and structured observations were reviewed.",
                            "Please verify any out-of-range values with your clinician.",
                        ],
                        "medical_terms_explained": [
                            {
                                "term": "Reference Range",
                                "explanation": (
                                    "The typical range of values observed in a healthy population "
                                    "for comparison."
                                ),
                            }
                        ],
                        "questions_for_doctor": [
                            "How do these results compare with my previous measurements?"
                        ],
                        "informational_disclaimer": (
                            "This summary is strictly informational and does not constitute "
                            "medical advice, diagnosis, or treatment."
                        ),
                    }
                )
        else:
            content = "Informational response generated by local mock provider."

        return GenerationResponse(
            content=content,
            provider=self.name,
            model=request.model or self.default_model,
            latency_ms=1.5,
            input_tokens=max(1, len(request.user_prompt) // 4),
            output_tokens=max(1, len(content) // 4),
        )

    async def embed(
        self, texts: list[str], *, model: str | None = None
    ) -> EmbeddingResponse:
        # Deterministic 16-dim normalized pseudo-embeddings for fast unit tests
        vectors: list[list[float]] = []
        for t in texts:
            digest = hashlib.sha256(t.encode("utf-8")).digest()
            vec = [round((b / 255.0) * 2.0 - 1.0, 4) for b in digest[:16]]
            vectors.append(vec)
        return EmbeddingResponse(
            embeddings=vectors,
            provider=self.name,
            model=model or "mock-embed-v1",
            dimensions=16,
            latency_ms=0.5,
        )

    async def health_check(self, *, timeout_seconds: float = 0.5) -> ProviderHealth:
        return ProviderHealth(
            provider=self.name,
            is_local=True,
            available=True,
            default_model=self.default_model,
            installed_models=[self.default_model],
            detail="Deterministic local mock provider ready.",
        )
