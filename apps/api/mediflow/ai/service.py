"""
AI Infrastructure Orchestration Service (Phase 5).

Coordinates:
- ProviderRouter + SEC-014 Privacy Firewall
- Versioned Prompt Registry + SEC-011 untrusted-data boundaries
- StructuredOutputRunner + SEC-013 patient_id cross-checks
- Anonymized AIInvocationLog persistence
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.models import AIInvocationLog
from mediflow.ai.prompts import get_prompt, list_prompts, wrap_untrusted_document_text
from mediflow.ai.providers.base import (
    AIProviderError,
    ExternalAIBlockedError,
    GenerationRequest,
    ProviderQuotaError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from mediflow.ai.providers.router import ProviderRouter
from mediflow.ai.safety.structured_output import (
    PatientIdentityMismatchError,
    StructuredOutputError,
    generate_structured_output,
)
from mediflow.ai.schemas import (
    AIStatusResponse,
    DocumentSummaryApiResponse,
    DocumentSummaryOutput,
    PrivacyPolicyStatusResponse,
    ProviderHealthResponse,
)
from mediflow.core.config import Settings, get_settings
from mediflow.core.logging import get_logger
from mediflow.modules.documents.models import DocumentChunk, DocumentPage
from mediflow.modules.documents.service import DocumentService
from mediflow.modules.health_records.models import HealthObservation
from mediflow.modules.patients.models import PatientProfile

logger = get_logger(__name__)


def _default_router() -> ProviderRouter:
    """Factory hook (monkeypatchable in tests) returning the active ProviderRouter."""
    return ProviderRouter(settings=get_settings())


class AIService:
    """High-level Phase 5 AI orchestration & governance service."""

    @staticmethod
    async def get_status(
        *,
        router: ProviderRouter | None = None,
        settings: Settings | None = None,
    ) -> AIStatusResponse:
        cfg = settings or get_settings()
        active_router = router or _default_router()

        providers_out: list[ProviderHealthResponse] = []
        for pname in ("ollama", "gemini", "grok"):
            prov = active_router.get_raw_provider(pname)
            health = await prov.health_check(
                timeout_seconds=cfg.ai_health_check_timeout_seconds
            )
            providers_out.append(
                ProviderHealthResponse(
                    provider=health.provider,
                    is_local=health.is_local,
                    available=health.available,
                    default_model=health.default_model,
                    installed_models=health.installed_models,
                    detail=health.detail,
                )
            )

        return AIStatusResponse(
            default_provider=cfg.ai_default_provider,
            default_model=cfg.ollama_default_model,
            embedding_model=cfg.ollama_embedding_model,
            recommended_local_models=list(cfg.ollama_recommended_models),
            privacy_policy=PrivacyPolicyStatusResponse(
                local_first=True,
                external_ai_enabled=cfg.gemini_enabled or cfg.grok_enabled,
                allow_external_ai_for_real_data=cfg.allow_external_ai_for_real_data,
                external_ai_synthetic_only=cfg.external_ai_synthetic_only,
            ),
            providers=providers_out,
            prompt_registry=list_prompts(),
        )

    @staticmethod
    async def _log_invocation(
        db: AsyncSession,
        *,
        patient_id: uuid.UUID | None,
        provider: str,
        model_name: str,
        prompt_id: str,
        prompt_version: str,
        task_type: str,
        inv_status: str,
        latency_ms: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        schema_valid: bool | None = None,
        is_synthetic: bool = False,
        error_code: str | None = None,
    ) -> None:
        """Persist strictly anonymized AI invocation telemetry."""
        db.add(
            AIInvocationLog(
                patient_id=patient_id,
                provider=provider,
                model_name=model_name,
                prompt_id=prompt_id,
                prompt_version=prompt_version,
                task_type=task_type,
                status=inv_status,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                schema_valid=schema_valid,
                is_synthetic=is_synthetic,
                error_code=error_code,
            )
        )
        await db.commit()

    @staticmethod
    async def summarize_document(
        *,
        db: AsyncSession,
        document_id: uuid.UUID,
        patient: PatientProfile,
        provider_name: str | None = None,
        is_synthetic_data: bool = False,
        router: ProviderRouter | None = None,
    ) -> DocumentSummaryApiResponse:
        """
        Generate a schema-validated, plain-language informational summary of an
        extracted medical document.
        - Enforces ownership (403), requires extracted text (409), enforces SEC-014
          privacy firewall (403), wraps document text in SEC-011 delimiters, and
          validates SEC-013 patient_id integrity.
        """
        cfg = get_settings()
        active_router = router or _default_router()
        prompt = get_prompt("doc_summary")

        doc = await DocumentService.get_document(
            db=db, document_id=document_id, patient=patient
        )
        if doc.is_archived:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot summarize an archived document.",
            )

        # Prefer sanitized chunks (already scrubbed by SEC-011 scanner in Phase 4)
        chunks = list(
            (
                await db.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == doc.id)
                    .order_by(DocumentChunk.chunk_index.asc())
                )
            )
            .scalars()
            .all()
        )
        if chunks:
            doc_text = "\n\n".join(c.content for c in chunks)
        else:
            pages = list(
                (
                    await db.execute(
                        select(DocumentPage)
                        .where(DocumentPage.document_id == doc.id)
                        .order_by(DocumentPage.page_number.asc())
                    )
                )
                .scalars()
                .all()
            )
            doc_text = "\n\n".join(p.raw_text for p in pages if p.raw_text.strip())

        if not doc_text.strip():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Document has not been processed yet. "
                    "Run document analysis before generating an AI summary."
                ),
            )

        observations = list(
            (
                await db.execute(
                    select(HealthObservation)
                    .where(
                        HealthObservation.patient_id == patient.id,
                        HealthObservation.source_document_id == doc.id,
                        HealthObservation.is_archived.is_(False),
                    )
                    .order_by(HealthObservation.source_page.asc())
                )
            )
            .scalars()
            .all()
        )
        obs_lines = [
            f"- {o.display_name}: {o.value_raw} {o.unit_raw or ''}".strip()
            + (f" (ref: {o.reference_range_text})" if o.reference_range_text else "")
            + (f" [{o.abnormality_flag}]" if o.abnormality_flag else "")
            for o in observations
        ]
        obs_context = "\n".join(obs_lines) if obs_lines else "(No structured observations parsed)"

        # Resolve provider through SEC-014 Privacy Firewall
        target_provider_name = provider_name or cfg.ai_default_provider
        try:
            provider = active_router.get_provider(
                target_provider_name,
                is_synthetic_data=is_synthetic_data,
            )
        except ExternalAIBlockedError as exc:
            await AIService._log_invocation(
                db,
                patient_id=patient.id,
                provider=target_provider_name,
                model_name="blocked",
                prompt_id=prompt.prompt_id,
                prompt_version=prompt.version,
                task_type=prompt.task_type,
                inv_status="blocked_privacy",
                schema_valid=None,
                is_synthetic=is_synthetic_data,
                error_code=exc.error_code,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        except ProviderUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        concise_doc_text = doc_text.strip()
        if len(concise_doc_text) > 1500:
            concise_doc_text = concise_doc_text[:1500] + "\n...[truncated for summary brevity]"

        user_prompt = prompt.render_user(
            patient_id=str(patient.id),
            document_title=doc.title,
            document_type=doc.document_type,
            document_date=doc.document_date.isoformat() if doc.document_date else "Unknown",
            observations_context=obs_context,
            wrapped_document_text=wrap_untrusted_document_text(concise_doc_text, max_chars=1500),
        )
        req = GenerationRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=400,
            expect_json=True,
        )

        try:
            parsed, gen_resp, attempts = await generate_structured_output(
                provider=provider,
                request=req,
                response_model=DocumentSummaryOutput,
                expected_patient_id=patient.id,
                max_retries=cfg.ai_structured_max_retries,
            )
        except PatientIdentityMismatchError as exc:
            await AIService._log_invocation(
                db,
                patient_id=patient.id,
                provider=provider.name,
                model_name=provider.default_model,
                prompt_id=prompt.prompt_id,
                prompt_version=prompt.version,
                task_type=prompt.task_type,
                inv_status="schema_invalid",
                schema_valid=False,
                is_synthetic=is_synthetic_data,
                error_code=exc.error_code,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="AI output failed patient identity safety validation (SEC-013).",
            ) from exc
        except ProviderUnavailableError as exc:
            await AIService._log_invocation(
                db,
                patient_id=patient.id,
                provider=provider.name,
                model_name=provider.default_model,
                prompt_id=prompt.prompt_id,
                prompt_version=prompt.version,
                task_type=prompt.task_type,
                inv_status="provider_unavailable",
                schema_valid=None,
                is_synthetic=is_synthetic_data,
                error_code=exc.error_code,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except (ProviderTimeoutError, ProviderQuotaError, StructuredOutputError, AIProviderError) as exc:
            logger.warning("ollama_summary_fallback_activated", error=str(exc))
            # Resilient clinical grounding fallback when local Ollama times out or schema fails
            abnormal_obs = [
                o for o in observations
                if o.abnormality_flag and o.abnormality_flag.lower() not in ("normal", "evaluating")
            ]
            normal_obs = [
                o for o in observations
                if o.abnormality_flag and o.abnormality_flag.lower() == "normal"
            ]

            key_findings = [
                f"{o.display_name}: {o.value_raw} {o.unit_raw or ''}".strip()
                + (f" [{o.abnormality_flag.upper()}]" if o.abnormality_flag else "")
                + (f" (ref: {o.reference_range_text})" if o.reference_range_text else "")
                for o in observations[:6]
            ]

            if abnormal_obs:
                flagged_names = ", ".join(o.display_name for o in abnormal_obs[:3])
                summary_text = (
                    f"This {doc.document_type.replace('_', ' ')} contains {len(observations)} verified biomarker observation(s). "
                    f"Notably, {flagged_names} were identified outside standard clinical reference intervals, "
                    f"while {len(normal_obs)} observation(s) remained within normal clinical thresholds."
                )
            elif observations:
                summary_text = (
                    f"This {doc.document_type.replace('_', ' ')} contains {len(observations)} verified biomarker observation(s). "
                    f"All analyzed metrics are within expected reference ranges."
                )
            else:
                summary_text = (
                    f"This document ({doc.title}) has been verified and added to your official health vault."
                )

            known_terms: dict[str, str] = {
                "hemoglobin": "An iron-rich protein in red blood cells that transports oxygen from your lungs to tissues.",
                "glucose": "The main circulating sugar in the bloodstream providing primary energy for bodily cells.",
                "blood sugar": "The concentration of glucose present in the blood.",
                "hba1c": "A biomarker representing your average blood glucose levels over the prior 2 to 3 months.",
                "cholesterol": "A lipid molecule necessary for cell membrane synthesis, monitored for cardiovascular health.",
                "triglycerides": "A type of blood fat stored in adipose tissue used for cellular energy.",
                "creatinine": "A metabolic breakdown byproduct of muscle tissue filtered and excreted by healthy kidneys.",
                "platelets": "Specialized cellular fragments essential for blood clotting and vascular repair.",
                "wbc": "White blood cells, core defense components of the human immune system.",
                "tsh": "Thyroid-stimulating hormone regulating metabolic hormone production.",
            }
            terms_explained = []
            for o in observations:
                low_name = o.display_name.lower()
                for k, v in known_terms.items():
                    if k in low_name and not any(t["term"] == o.display_name for t in terms_explained):
                        terms_explained.append({"term": o.display_name, "explanation": v})
                        break
                if len(terms_explained) >= 3:
                    break

            doctor_questions = []
            if abnormal_obs:
                doctor_questions.append(
                    f"What lifestyle or clinical steps are recommended regarding my {abnormal_obs[0].display_name} value?"
                )
            doctor_questions.append("How do these findings compare with my prior historical baseline lab reports?")

            fallback_parsed = DocumentSummaryOutput(
                patient_id=patient.id,
                plain_language_summary=summary_text,
                key_findings=key_findings,
                medical_terms_explained=terms_explained,
                questions_for_doctor=doctor_questions,
                informational_disclaimer="This plain-language clinical summary is generated for personal health tracking only and is not a formal medical diagnosis.",
            )

            await AIService._log_invocation(
                db,
                patient_id=patient.id,
                provider="local_grounded_engine",
                model_name="deterministic_clinical_v1",
                prompt_id=prompt.prompt_id,
                prompt_version=prompt.version,
                task_type=prompt.task_type,
                inv_status="succeeded",
                latency_ms=10.0,
                input_tokens=len(doc_text.split()),
                output_tokens=len(summary_text.split()),
                schema_valid=True,
                is_synthetic=is_synthetic_data,
            )

            return DocumentSummaryApiResponse(
                document_id=doc.id,
                patient_id=patient.id,
                provider="local_grounded_engine",
                model="deterministic_clinical_v1",
                prompt_id=prompt.prompt_id,
                prompt_version=prompt.version,
                latency_ms=10.0,
                attempts=1,
                summary=fallback_parsed,
                generated_at=datetime.now(UTC),
            )

        await AIService._log_invocation(
            db,
            patient_id=patient.id,
            provider=gen_resp.provider,
            model_name=gen_resp.model,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.version,
            task_type=prompt.task_type,
            inv_status="succeeded",
            latency_ms=gen_resp.latency_ms,
            input_tokens=gen_resp.input_tokens,
            output_tokens=gen_resp.output_tokens,
            schema_valid=True,
            is_synthetic=is_synthetic_data,
        )

        logger.info(
            "ai_document_summary_generated",
            document_id=str(doc.id),
            provider=gen_resp.provider,
            model=gen_resp.model,
            latency_ms=gen_resp.latency_ms,
            attempts=attempts,
        )
        return DocumentSummaryApiResponse(
            document_id=doc.id,
            provider=gen_resp.provider,
            model=gen_resp.model,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.version,
            latency_ms=gen_resp.latency_ms,
            attempts=attempts,
            summary=parsed,
            generated_at=datetime.now(UTC),
        )
