"""
Phase 5 Evaluation Harness — Structured Output Validity (AIR-001),
SEC-013 Patient Identity Enforcement, SEC-014 Privacy Firewall, and
Live Ollama Connectivity Check.
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from mediflow.ai.prompts import get_prompt, wrap_untrusted_document_text  # noqa: E402
from mediflow.ai.providers.base import ExternalAIBlockedError, GenerationRequest  # noqa: E402
from mediflow.ai.providers.external import GeminiProvider  # noqa: E402
from mediflow.ai.providers.mock import MockAIProvider  # noqa: E402
from mediflow.ai.providers.ollama import OllamaProvider  # noqa: E402
from mediflow.ai.providers.router import PrivacyPolicyGuard  # noqa: E402
from mediflow.ai.safety.structured_output import (  # noqa: E402
    PatientIdentityMismatchError,
    generate_structured_output,
)
from mediflow.ai.schemas import DocumentSummaryOutput  # noqa: E402
from mediflow.core.config import get_settings  # noqa: E402


async def run_evaluation() -> dict[str, Any]:
    settings = get_settings()
    ollama = OllamaProvider(
        base_url=settings.ollama_base_url,
        default_model=settings.ollama_default_model,
        embedding_model=settings.ollama_embedding_model,
    )
    ollama_health = await ollama.health_check(timeout_seconds=1.0)

    # Evaluate AIR-001 (Structured Output Validity Rate) on 20 synthetic cases
    prompt = get_prompt("doc_summary")
    total_cases = 20
    valid_cases = 0
    provider: OllamaProvider | MockAIProvider = (
        ollama
        if ollama_health.available
        and any(m.startswith(settings.ollama_default_model) for m in ollama_health.installed_models)
        else MockAIProvider()
    )

    for idx in range(total_cases):
        pid = uuid.uuid4()
        req = GenerationRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.render_user(
                patient_id=str(pid),
                document_title=f"Synthetic Lab Report #{idx + 1}",
                document_type="lab_report",
                document_date="2026-11-10",
                observations_context="- Hemoglobin: 13.5 g/dL (ref: 12.0 - 16.0)",
                wrapped_document_text=wrap_untrusted_document_text(
                    "SYNTHETIC LAB REPORT\nHemoglobin 13.5 g/dL (12.0 - 16.0)"
                ),
            ),
            expect_json=True,
        )
        try:
            await generate_structured_output(
                provider=provider,
                request=req,
                response_model=DocumentSummaryOutput,
                expected_patient_id=pid,
                max_retries=1,
            )
            valid_cases += 1
        except Exception as exc:
            print(f"Case {idx + 1} failed validation: {exc}", file=sys.stderr)

    # Verify SEC-013 foreign patient_id rejection
    sec013_passed = False
    foreign_resp = json.dumps(
        {
            "patient_id": str(uuid.uuid4()),
            "plain_language_summary": "Foreign patient summary test.",
            "key_findings": [],
            "medical_terms_explained": [],
            "questions_for_doctor": [],
            "informational_disclaimer": "Informational only; not medical advice.",
        }
    )
    try:
        await generate_structured_output(
            provider=MockAIProvider(response_sequence=[foreign_resp]),
            request=GenerationRequest(system_prompt="s", user_prompt="u"),
            response_model=DocumentSummaryOutput,
            expected_patient_id=uuid.uuid4(),
            max_retries=0,
        )
    except PatientIdentityMismatchError:
        sec013_passed = True

    # Verify SEC-014 privacy firewall
    sec014_passed = False
    try:
        PrivacyPolicyGuard.assert_provider_allowed(
            GeminiProvider(api_key="synthetic", enabled=True),
            settings=settings,
            is_synthetic_data=False,
        )
    except ExternalAIBlockedError:
        sec014_passed = True

    return {
        "evaluation_provider": provider.name,
        "ollama_live_reachable": ollama_health.available,
        "ollama_installed_models": ollama_health.installed_models,
        "ollama_setup_hint": (
            None
            if ollama_health.available
            else f"ollama pull {settings.ollama_default_model} && "
            f"ollama pull {settings.ollama_embedding_model}"
        ),
        "AIR-001_StructuredOutputValidity": round(valid_cases / total_cases, 4),
        "AIR-001_TotalCases": total_cases,
        "SEC-013_PatientIdValidation": "PASSED" if sec013_passed else "FAILED",
        "SEC-014_ExternalPrivacyFirewall": "PASSED" if sec014_passed else "FAILED",
    }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run_evaluation()), indent=2))
