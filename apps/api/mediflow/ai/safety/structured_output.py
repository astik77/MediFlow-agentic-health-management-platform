"""
Structured Output Validator & SEC-013 Patient Identity Cross-Check (Phase 5).

Ensures LLM outputs strictly conform to Pydantic v2 schemas (AIR-001) and that
no model hallucination can emit a foreign patient_id (SEC-013).
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from mediflow.ai.providers.base import AIProvider, GenerationRequest, GenerationResponse

ModelT = TypeVar("ModelT", bound=BaseModel)

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class StructuredOutputError(Exception):
    """Raised when AI output fails JSON parsing or Pydantic schema validation."""

    error_code: str = "schema_validation_failed"


class PatientIdentityMismatchError(StructuredOutputError):
    """SEC-013: Raised when AI output contains a hallucinated foreign patient_id."""

    error_code = "sec013_patient_id_mismatch"


@dataclass(slots=True)
class StructuredRunResult:
    """Result bundle from StructuredOutputRunner."""

    parsed: BaseModel
    response: GenerationResponse
    attempts: int


def extract_json_text(raw: str) -> str:
    """
    Extract a JSON object/array from raw LLM output, handling markdown fences
    and leading/trailing conversational filler safely.
    """
    text = raw.strip()
    fence_match = _CODE_FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()

    if text.startswith("{") or text.startswith("["):
        return text

    # Locate outermost JSON object bounds
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]

    return text


def enforce_output_patient_id(parsed: BaseModel, expected_patient_id: uuid.UUID) -> None:
    """
    SEC-013 invariant: If the structured AI output carries a `patient_id` attribute,
    it MUST match the authenticated session's patient_id exactly.
    """
    if not hasattr(parsed, "patient_id"):
        return
    emitted = parsed.patient_id
    if emitted is None:
        return
    try:
        emitted_uuid = emitted if isinstance(emitted, uuid.UUID) else uuid.UUID(str(emitted))
    except ValueError as exc:
        raise PatientIdentityMismatchError(
            "AI output emitted an invalid patient_id format (SEC-013)."
        ) from exc

    if emitted_uuid != expected_patient_id:
        raise PatientIdentityMismatchError(
            "AI output emitted a foreign patient_id that does not match the "
            "authenticated session (SEC-013)."
        )


async def generate_structured_output(
    *,
    provider: AIProvider,
    request: GenerationRequest,
    response_model: type[ModelT],
    expected_patient_id: uuid.UUID | None = None,
    max_retries: int = 1,
) -> tuple[ModelT, GenerationResponse, int]:
    """
    Invoke *provider* with JSON mode enabled, validate against *response_model*,
    retry up to *max_retries* times with explicit validation feedback, and enforce
    SEC-013 patient_id alignment.
    """
    schema_dict = response_model.model_json_schema()
    current_req = GenerationRequest(
        system_prompt=request.system_prompt,
        user_prompt=request.user_prompt,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        expect_json=True,
        json_schema=schema_dict,
    )

    last_error = ""

    for attempt in range(1, max_retries + 2):
        response = await provider.generate(current_req)
        json_str = extract_json_text(response.content)
        try:
            raw_obj = json.loads(json_str)
            parsed = response_model.model_validate(raw_obj)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)[:400]
            if attempt <= max_retries:
                current_req = GenerationRequest(
                    system_prompt=request.system_prompt,
                    user_prompt=(
                        f"{request.user_prompt}\n\n"
                        f"Your previous response did not match the required JSON schema.\n"
                        f"Validation error: {last_error}\n"
                        "Return ONLY a valid JSON object matching the exact schema."
                    ),
                    model=request.model,
                    temperature=0.0,
                    max_tokens=request.max_tokens,
                    expect_json=True,
                    json_schema=schema_dict,
                )
                continue
            raise StructuredOutputError(
                f"AI response failed schema validation after {attempt} attempt(s): {last_error}"
            ) from exc

        if expected_patient_id is not None:
            enforce_output_patient_id(parsed, expected_patient_id)

        return parsed, response, attempt

    raise StructuredOutputError(f"Structured generation failed: {last_error}")
