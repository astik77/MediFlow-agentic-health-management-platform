"""
Analytics, Biomarker Trends & 7-Day Longitudinal Summary Service (Phase 8).

Security & Governance Invariants:
- SEC-001 / SEC-002: Every query filters strictly by authenticated patient_id.
- Candidate Governance: Unconfirmed 'candidate' observations NEVER enter biomarker
  trend charts or summary metrics; they are isolated to pending review queues.
- SEC-013 & SEC-014: Local AI summary synthesis uses local-only provider routing
  and validates patient_id on structured outputs, falling back cleanly to a
  deterministic statistical summary whenever Ollama is offline or validation fails.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.prompts import get_prompt
from mediflow.ai.providers.base import AIProviderError, GenerationRequest
from mediflow.ai.providers.router import ProviderRouter
from mediflow.ai.safety.structured_output import (
    PatientIdentityMismatchError,
    StructuredOutputError,
    generate_structured_output,
)
from mediflow.ai.service import AIService
from mediflow.core.config import get_settings
from mediflow.core.logging import get_logger
from mediflow.modules.analytics.models import HealthSummary
from mediflow.modules.analytics.schemas import (
    DEFAULT_SUMMARY_DISCLAIMER,
    AbnormalObservationAlert,
    AvailableBiomarkerItem,
    BiomarkerTrendsResponse,
    DashboardKPIs,
    DashboardResponse,
    HealthSummaryAIOutput,
    HealthSummaryListResponse,
    HealthSummaryMetricsSnapshot,
    HealthSummaryResponse,
    NotableTrendItem,
    PendingReviewItem,
    TrendWindow,
)
from mediflow.modules.analytics.trends import build_biomarker_trend_series, ensure_utc
from mediflow.modules.conversations.models import Message
from mediflow.modules.documents.models import Document
from mediflow.modules.health_records.models import (
    HealthEvent,
    HealthObservation,
    PatientAllergy,
    PatientCondition,
    PatientSymptom,
)
from mediflow.modules.patients.models import PatientProfile

logger = get_logger(__name__)

_ABNORMAL_FLAGS = frozenset({"low", "high", "critical"})


def _default_router() -> ProviderRouter:
    """Factory hook (monkeypatchable in tests) returning the active ProviderRouter."""
    return ProviderRouter(settings=get_settings())


def _summary_row_to_response(row: HealthSummary) -> HealthSummaryResponse:
    """Convert a persisted HealthSummary ORM row into its API response schema."""
    snapshot = HealthSummaryMetricsSnapshot.model_validate(row.metrics_snapshot_json or {})
    notable = [NotableTrendItem.model_validate(item) for item in (row.notable_trends_json or [])]
    mode = (
        "local_ai"
        if row.generation_mode == "local_ai"
        else "deterministic_fallback"
    )
    return HealthSummaryResponse(
        id=row.id,
        window_days=row.window_days,
        period_start=ensure_utc(row.period_start),
        period_end=ensure_utc(row.period_end),
        headline=row.headline,
        summary_text=row.summary_text,
        highlights=list(row.highlights_json or []),
        notable_trends=notable,
        questions_for_doctor=list(row.questions_for_doctor_json or []),
        metrics_snapshot=snapshot,
        generation_mode=mode,
        model_name=row.model_name,
        prompt_version=row.prompt_version,
        informational_disclaimer=DEFAULT_SUMMARY_DISCLAIMER,
        created_at=ensure_utc(row.created_at),
    )


def _build_deterministic_summary(
    *,
    window_days: int,
    snapshot: HealthSummaryMetricsSnapshot,
    notable_trends: list[NotableTrendItem],
    ongoing_symptoms: list[PatientSymptom],
    active_conditions: list[PatientCondition],
) -> tuple[str, str, list[str], list[str]]:
    """
    Generate a clean, accurate, strictly informational longitudinal health summary
    purely from deterministic statistics when local AI is offline or unavailable.
    """
    if (
        snapshot.observations_in_window == 0
        and snapshot.symptoms_logged_in_window == 0
        and snapshot.documents_uploaded_in_window == 0
    ):
        headline = f"{window_days}-Day Health Summary: Steady Period (No New Entries)"
        summary_text = (
            f"No new confirmed lab observations, symptoms, or documents were recorded in the "
            f"past {window_days} days. You currently have {snapshot.active_conditions_total} "
            f"active condition(s) and {snapshot.ongoing_symptoms_total} ongoing symptom(s) "
            f"on file."
        )
    elif snapshot.abnormal_observations_in_window > 0:
        headline = (
            f"{window_days}-Day Health Summary: "
            f"{snapshot.abnormal_observations_in_window} Out-of-Range Observation(s) Noted"
        )
        summary_text = (
            f"Over the last {window_days} days, {snapshot.observations_in_window} confirmed "
            f"observation(s) were recorded, including {snapshot.abnormal_observations_in_window} "
            f"flagged outside the reference range, alongside {snapshot.symptoms_logged_in_window} "
            f"newly logged symptom(s) and {snapshot.documents_uploaded_in_window} uploaded "
            f"document(s). Review the highlighted markers below with your healthcare provider."
        )
    else:
        headline = f"{window_days}-Day Health Summary: All Recent Observations Within Range"
        summary_text = (
            f"Over the last {window_days} days, {snapshot.observations_in_window} confirmed "
            f"observation(s) were recorded with none flagged out of range, alongside "
            f"{snapshot.symptoms_logged_in_window} newly logged symptom(s) and "
            f"{snapshot.documents_uploaded_in_window} uploaded document(s)."
        )

    highlights: list[str] = [
        (
            f"Confirmed observations in window: {snapshot.observations_in_window} "
            f"({snapshot.abnormal_observations_in_window} out-of-range)."
        ),
        (
            f"Symptoms logged in window: {snapshot.symptoms_logged_in_window} "
            f"(total ongoing: {snapshot.ongoing_symptoms_total})."
        ),
        f"Documents uploaded in window: {snapshot.documents_uploaded_in_window}.",
    ]
    if active_conditions:
        cond_names = ", ".join(c.name for c in active_conditions[:4])
        highlights.append(f"Active conditions on file: {cond_names}.")
    if ongoing_symptoms:
        sym_names = ", ".join(f"{s.name} ({s.severity})" for s in ongoing_symptoms[:4])
        highlights.append(f"Ongoing symptoms: {sym_names}.")
    for nt in notable_trends[:3]:
        flag_note = f" [{nt.abnormality_flag}]" if nt.abnormality_flag else ""
        delta_note = f" ({nt.delta_percent:+.1f}%)" if nt.delta_percent is not None else ""
        unit_str = f" {nt.unit}" if nt.unit else ""
        highlights.append(
            f"{nt.biomarker}: latest {nt.latest_value}{unit_str}{delta_note}{flag_note}."
        )
    if snapshot.pending_candidates_excluded > 0:
        highlights.append(
            f"{snapshot.pending_candidates_excluded} unconfirmed extracted observation(s) "
            "were excluded pending your review."
        )

    questions: list[str] = []
    if notable_trends:
        top_names = ", ".join(nt.biomarker for nt in notable_trends[:3])
        questions.append(
            f"Could we review my recent {top_names} trend(s) and whether "
            "follow-up testing is needed?"
        )
    if ongoing_symptoms:
        questions.append(
            "Do my ongoing symptoms correlate with any of my recent lab results or conditions?"
        )
    if not questions:
        questions.append(
            "Are there any routine preventive screenings or baseline labs "
            "recommended at my next visit?"
        )

    return headline, summary_text, highlights, questions


class AnalyticsService:
    """Domain service for patient dashboard analytics, biomarker trends, and 7-day summaries."""

    @staticmethod
    async def get_dashboard(
        db: AsyncSession,
        patient: PatientProfile,
    ) -> DashboardResponse:
        """Aggregate patient-scoped KPIs, alerts, review queue, trend list, and latest summary."""
        # 1. Active confirmed conditions
        active_conditions_count = int(
            (
                await db.execute(
                    select(func.count(PatientCondition.id)).where(
                        PatientCondition.patient_id == patient.id,
                        PatientCondition.status == "active",
                        PatientCondition.review_status == "confirmed",
                        PatientCondition.is_archived.is_(False),
                    )
                )
            ).scalar_one()
        )

        # 2. Active confirmed allergies
        active_allergies_count = int(
            (
                await db.execute(
                    select(func.count(PatientAllergy.id)).where(
                        PatientAllergy.patient_id == patient.id,
                        PatientAllergy.status == "active",
                        PatientAllergy.review_status == "confirmed",
                        PatientAllergy.is_archived.is_(False),
                    )
                )
            ).scalar_one()
        )

        # 3. Ongoing confirmed symptoms
        ongoing_symptoms_count = int(
            (
                await db.execute(
                    select(func.count(PatientSymptom.id)).where(
                        PatientSymptom.patient_id == patient.id,
                        PatientSymptom.status == "ongoing",
                        PatientSymptom.review_status == "confirmed",
                        PatientSymptom.is_archived.is_(False),
                    )
                )
            ).scalar_one()
        )

        # 4. Non-archived documents
        docs = list(
            (
                await db.execute(
                    select(Document).where(
                        Document.patient_id == patient.id,
                        Document.is_archived.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        docs_by_id = {d.id: d for d in docs}

        # 5. Confirmed observations (for KPIs, abnormal alerts, and trend list)
        confirmed_obs = list(
            (
                await db.execute(
                    select(HealthObservation)
                    .where(
                        HealthObservation.patient_id == patient.id,
                        HealthObservation.review_status == "confirmed",
                        HealthObservation.is_archived.is_(False),
                    )
                    .order_by(HealthObservation.observed_at.desc())
                )
            )
            .scalars()
            .all()
        )

        abnormal_obs = [
            o for o in confirmed_obs if (o.abnormality_flag or "").lower() in _ABNORMAL_FLAGS
        ]
        recent_abnormal = [
            AbnormalObservationAlert(
                id=o.id,
                display_name=o.display_name,
                value_raw=o.value_raw,
                unit_raw=o.unit_raw,
                reference_range_text=o.reference_range_text,
                abnormality_flag=(o.abnormality_flag or "unknown").lower(),
                observed_at=ensure_utc(o.observed_at),
                source_document_id=o.source_document_id,
            )
            for o in abnormal_obs[:6]
        ]

        # 6. Pending extracted candidates (strictly isolated from confirmed metrics)
        candidate_obs = list(
            (
                await db.execute(
                    select(HealthObservation).where(
                        HealthObservation.patient_id == patient.id,
                        HealthObservation.review_status == "candidate",
                        HealthObservation.is_archived.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        pending_by_doc: dict[uuid.UUID, int] = defaultdict(int)
        for cand in candidate_obs:
            if cand.source_document_id is not None and cand.source_document_id in docs_by_id:
                pending_by_doc[cand.source_document_id] += 1

        pending_review_documents = [
            PendingReviewItem(
                document_id=doc_id,
                document_title=docs_by_id[doc_id].title,
                document_type=docs_by_id[doc_id].document_type,
                pending_count=cnt,
                uploaded_at=ensure_utc(docs_by_id[doc_id].uploaded_at),
            )
            for doc_id, cnt in pending_by_doc.items()
        ]
        pending_review_documents.sort(key=lambda item: item.uploaded_at, reverse=True)

        # 7. Pending AI-proposed symptom drafts from Phase 6 Assistant
        proposal_msgs = list(
            (
                await db.execute(
                    select(Message.proposed_action_json).where(
                        Message.patient_id == patient.id,
                        Message.proposed_action_json.is_not(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        pending_symptom_proposals_count = sum(
            1
            for prop in proposal_msgs
            if isinstance(prop, dict) and prop.get("status") == "pending"
        )

        # 8. Available biomarker trend series
        all_series = build_biomarker_trend_series(confirmed_obs, window="all")
        available_biomarkers = [
            AvailableBiomarkerItem(
                biomarker_key=s.biomarker_key,
                display_name=s.display_name,
                unit=s.unit,
                point_count=s.point_count,
                latest_value=s.latest_value,
                latest_abnormality_flag=s.latest_abnormality_flag,
                direction=s.direction,
            )
            for s in all_series
        ]

        # 9. Latest persisted longitudinal health summary
        latest_summary_row = (
            await db.execute(
                select(HealthSummary)
                .where(HealthSummary.patient_id == patient.id)
                .order_by(HealthSummary.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        return DashboardResponse(
            kpis=DashboardKPIs(
                active_conditions_count=active_conditions_count,
                active_allergies_count=active_allergies_count,
                ongoing_symptoms_count=ongoing_symptoms_count,
                confirmed_observations_count=len(confirmed_obs),
                abnormal_observations_count=len(abnormal_obs),
                documents_count=len(docs),
                pending_candidates_count=len(candidate_obs),
                pending_symptom_proposals_count=pending_symptom_proposals_count,
            ),
            recent_abnormal_observations=recent_abnormal,
            pending_review_documents=pending_review_documents,
            available_biomarkers=available_biomarkers,
            latest_summary=(
                _summary_row_to_response(latest_summary_row)
                if latest_summary_row is not None
                else None
            ),
            generated_at=datetime.now(UTC),
        )

    @staticmethod
    async def get_trends(
        db: AsyncSession,
        patient: PatientProfile,
        *,
        window: TrendWindow = "all",
        biomarker: str | None = None,
    ) -> BiomarkerTrendsResponse:
        """Compute patient-scoped longitudinal biomarker trend series."""
        confirmed_obs = list(
            (
                await db.execute(
                    select(HealthObservation)
                    .where(
                        HealthObservation.patient_id == patient.id,
                        HealthObservation.review_status == "confirmed",
                        HealthObservation.is_archived.is_(False),
                    )
                    .order_by(HealthObservation.observed_at.asc())
                )
            )
            .scalars()
            .all()
        )
        series = build_biomarker_trend_series(
            confirmed_obs,
            window=window,
            biomarker_filter=biomarker,
        )
        return BiomarkerTrendsResponse(
            window=window,
            biomarker_filter=biomarker.strip() if biomarker and biomarker.strip() else None,
            series_count=len(series),
            series=series,
        )

    @staticmethod
    async def generate_summary(
        db: AsyncSession,
        patient: PatientProfile,
        *,
        window_days: int = 7,
        router: ProviderRouter | None = None,
    ) -> HealthSummaryResponse:
        """
        Generate, persist, and timeline-log a longitudinal health summary for the
        last `window_days` days (default 7).
        Uses local AI (health_summary_7d@1.0.0) with SEC-013/SEC-014 enforcement when
        available, falling back seamlessly to a deterministic statistical summary.
        """
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=window_days)

        # Fetch confirmed patient records (strictly patient-scoped)
        confirmed_obs = list(
            (
                await db.execute(
                    select(HealthObservation)
                    .where(
                        HealthObservation.patient_id == patient.id,
                        HealthObservation.review_status == "confirmed",
                        HealthObservation.is_archived.is_(False),
                    )
                    .order_by(HealthObservation.observed_at.asc())
                )
            )
            .scalars()
            .all()
        )
        obs_in_window = [
            o for o in confirmed_obs if ensure_utc(o.observed_at) >= period_start
        ]
        abnormal_in_window = [
            o for o in obs_in_window if (o.abnormality_flag or "").lower() in _ABNORMAL_FLAGS
        ]

        pending_candidates_excluded = int(
            (
                await db.execute(
                    select(func.count(HealthObservation.id)).where(
                        HealthObservation.patient_id == patient.id,
                        HealthObservation.review_status == "candidate",
                        HealthObservation.is_archived.is_(False),
                    )
                )
            ).scalar_one()
        )

        symptoms = list(
            (
                await db.execute(
                    select(PatientSymptom).where(
                        PatientSymptom.patient_id == patient.id,
                        PatientSymptom.review_status == "confirmed",
                        PatientSymptom.is_archived.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        symptoms_in_window = [s for s in symptoms if ensure_utc(s.started_at) >= period_start]
        ongoing_symptoms = [s for s in symptoms if s.status == "ongoing"]

        active_conditions = list(
            (
                await db.execute(
                    select(PatientCondition).where(
                        PatientCondition.patient_id == patient.id,
                        PatientCondition.status == "active",
                        PatientCondition.review_status == "confirmed",
                        PatientCondition.is_archived.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )

        active_allergies = list(
            (
                await db.execute(
                    select(PatientAllergy).where(
                        PatientAllergy.patient_id == patient.id,
                        PatientAllergy.status == "active",
                        PatientAllergy.review_status == "confirmed",
                        PatientAllergy.is_archived.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )

        docs = list(
            (
                await db.execute(
                    select(Document).where(
                        Document.patient_id == patient.id,
                        Document.is_archived.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        docs_in_window = [d for d in docs if ensure_utc(d.uploaded_at) >= period_start]

        # Build notable trends from confirmed observations (all-time active/abnormal series)
        all_series = build_biomarker_trend_series(confirmed_obs, window="all")
        notable_trends: list[NotableTrendItem] = []
        for s in all_series:
            is_abnormal = (s.latest_abnormality_flag or "").lower() in _ABNORMAL_FLAGS
            is_moving = s.direction in ("increasing", "decreasing")
            is_recent = s.latest_observed_at >= period_start
            if is_abnormal or (is_moving and is_recent) or is_recent:
                notable_trends.append(
                    NotableTrendItem(
                        biomarker=s.display_name,
                        latest_value=s.latest_value,
                        unit=s.unit,
                        direction=s.direction,
                        delta_percent=s.delta_percent,
                        abnormality_flag=s.latest_abnormality_flag,
                        reference_range_text=s.reference_range_text,
                    )
                )
        notable_trends = notable_trends[:8]

        snapshot = HealthSummaryMetricsSnapshot(
            observations_in_window=len(obs_in_window),
            abnormal_observations_in_window=len(abnormal_in_window),
            symptoms_logged_in_window=len(symptoms_in_window),
            ongoing_symptoms_total=len(ongoing_symptoms),
            documents_uploaded_in_window=len(docs_in_window),
            active_conditions_total=len(active_conditions),
            pending_candidates_excluded=pending_candidates_excluded,
        )

        # Always compute deterministic fallback baseline first
        headline, summary_text, highlights, questions = _build_deterministic_summary(
            window_days=window_days,
            snapshot=snapshot,
            notable_trends=notable_trends,
            ongoing_symptoms=ongoing_symptoms,
            active_conditions=active_conditions,
        )
        generation_mode = "deterministic_fallback"
        model_name: str | None = None
        prompt_version: str | None = None

        # Attempt local AI synthesis (SEC-014 local-only + SEC-013 patient_id check)
        cfg = get_settings()
        active_router = router or _default_router()
        prompt = get_prompt("health_summary_7d")
        try:
            provider = active_router.get_provider(
                cfg.ai_default_provider,
                is_synthetic_data=False,
            )
            metrics_context = (
                f"- Confirmed observations in window: {snapshot.observations_in_window} "
                f"({snapshot.abnormal_observations_in_window} abnormal)\n"
                f"- Symptoms logged in window: {snapshot.symptoms_logged_in_window} "
                f"(ongoing total: {snapshot.ongoing_symptoms_total})\n"
                f"- Documents uploaded in window: {snapshot.documents_uploaded_in_window}\n"
                f"- Active conditions: {snapshot.active_conditions_total}\n"
                f"- Pending unconfirmed candidates excluded: {snapshot.pending_candidates_excluded}"
            )
            trends_lines = [
                f"- {nt.biomarker}: {nt.latest_value} {nt.unit or ''} "
                f"(direction: {nt.direction}, flag: {nt.abnormality_flag or 'normal'}, "
                f"ref: {nt.reference_range_text or 'n/a'})".strip()
                for nt in notable_trends
            ]
            trends_context = "\n".join(trends_lines) if trends_lines else "(No numeric trends)"
            clinical_lines = [
                "Conditions: "
                + (", ".join(c.name for c in active_conditions) if active_conditions else "None"),
                "Allergies: "
                + (", ".join(a.allergen for a in active_allergies) if active_allergies else "None"),
                "Ongoing Symptoms: "
                + (
                    ", ".join(f"{s.name} ({s.severity})" for s in ongoing_symptoms)
                    if ongoing_symptoms
                    else "None"
                ),
            ]
            user_prompt = prompt.render_user(
                patient_id=str(patient.id),
                window_days=str(window_days),
                period_start=period_start.date().isoformat(),
                period_end=period_end.date().isoformat(),
                metrics_context=metrics_context,
                trends_context=trends_context,
                clinical_context="\n".join(clinical_lines),
            )
            req = GenerationRequest(
                system_prompt=prompt.system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=900,
                expect_json=True,
            )
            parsed, gen_resp, _ = await generate_structured_output(
                provider=provider,
                request=req,
                response_model=HealthSummaryAIOutput,
                expected_patient_id=patient.id,
                max_retries=cfg.ai_structured_max_retries,
            )
            headline = parsed.headline.strip()[:255]
            summary_text = parsed.summary_text.strip()
            if parsed.highlights:
                highlights = [h.strip() for h in parsed.highlights if h.strip()]
            if parsed.questions_for_doctor:
                questions = [q.strip() for q in parsed.questions_for_doctor if q.strip()]
            generation_mode = "local_ai"
            model_name = gen_resp.model
            prompt_version = prompt.version

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
                is_synthetic=False,
            )
        except PatientIdentityMismatchError as exc:
            logger.warning(
                "health_summary_sec013_fallback",
                patient_id=str(patient.id),
                error_code=exc.error_code,
            )
            await AIService._log_invocation(
                db,
                patient_id=patient.id,
                provider=cfg.ai_default_provider,
                model_name="fallback",
                prompt_id=prompt.prompt_id,
                prompt_version=prompt.version,
                task_type=prompt.task_type,
                inv_status="schema_invalid",
                schema_valid=False,
                is_synthetic=False,
                error_code=exc.error_code,
            )
        except (StructuredOutputError, AIProviderError) as exc:
            logger.info(
                "health_summary_deterministic_fallback",
                patient_id=str(patient.id),
                reason=exc.error_code,
            )

        summary_row = HealthSummary(
            id=uuid.uuid4(),
            patient_id=patient.id,
            window_days=window_days,
            period_start=period_start,
            period_end=period_end,
            headline=headline,
            summary_text=summary_text,
            highlights_json=highlights,
            notable_trends_json=[nt.model_dump() for nt in notable_trends],
            questions_for_doctor_json=questions,
            metrics_snapshot_json=snapshot.model_dump(),
            generation_mode=generation_mode,
            model_name=model_name,
            prompt_version=prompt_version,
        )
        db.add(summary_row)

        # Record a 'summary' event on the patient's Medical Timeline
        db.add(
            HealthEvent(
                id=uuid.uuid4(),
                patient_id=patient.id,
                event_category="summary",
                title=f"{window_days}-Day Health Summary",
                summary=headline,
                event_occurred_at=period_end,
                source_type="ai_proposed" if generation_mode == "local_ai" else "patient_reported",
                review_status="confirmed",
                related_entity_type="health_summary",
                related_entity_id=summary_row.id,
                metadata_json={
                    "window_days": window_days,
                    "generation_mode": generation_mode,
                },
            )
        )

        await db.commit()
        await db.refresh(summary_row)
        return _summary_row_to_response(summary_row)

    @staticmethod
    async def list_summaries(
        db: AsyncSession,
        patient: PatientProfile,
        *,
        limit: int = 20,
    ) -> HealthSummaryListResponse:
        """List patient's persisted historical health summaries (newest first)."""
        rows = list(
            (
                await db.execute(
                    select(HealthSummary)
                    .where(HealthSummary.patient_id == patient.id)
                    .order_by(HealthSummary.created_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        items = [_summary_row_to_response(r) for r in rows]
        return HealthSummaryListResponse(items=items, total=len(items))
