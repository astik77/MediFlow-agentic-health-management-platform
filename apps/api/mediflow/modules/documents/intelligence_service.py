"""
Document Intelligence & Candidate Review Service (Phase 4).

Orchestrates:
- Idempotent document processing jobs (SEC-017)
- PDF text extraction + local RapidOCR pipeline
- SEC-011 prompt injection scanning & quarantine
- Deterministic document classification & clinical date/observation parsing
- Candidate-vs-Confirmed patient review workflow with immutable RecordRevision audit trail
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, date, datetime
from datetime import time as dt_time
from pathlib import Path
from typing import Any

import structlog
from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.rag.service import RagService
from mediflow.core.config import get_settings
from mediflow.core.dependencies import enforce_patient_ownership
from mediflow.modules.documents.models import (
    Document,
    DocumentChunk,
    DocumentEmbedding,
    DocumentPage,
    DocumentProcessingJob,
)
from mediflow.modules.documents.pipeline.chunker import build_document_chunks
from mediflow.modules.documents.pipeline.classifier import classify_document
from mediflow.modules.documents.pipeline.clinical_parser import (
    CandidateObservation,
    extract_clinical_date,
    parse_candidate_observations,
)
from mediflow.modules.documents.pipeline.injection_scanner import scan_page_text
from mediflow.modules.documents.pipeline.ocr_engine import OcrBackend
from mediflow.modules.documents.pipeline.pdf_extractor import extract_document_pages
from mediflow.modules.documents.schemas import CandidateReviewRequest
from mediflow.modules.documents.service import DocumentService, _assert_within_storage_root
from mediflow.modules.health_records.models import HealthEvent, HealthObservation
from mediflow.modules.health_records.service import (
    OBSERVATION_FIELDS,
    HealthRecordsService,
    _serialize_snapshot,
    _try_parse_float,
)
from mediflow.modules.patients.models import PatientProfile

logger = structlog.get_logger(__name__)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _date_to_utc(d: date | None) -> datetime:
    if d is None:
        return _utc_now()
    return datetime.combine(d, dt_time.min, tzinfo=UTC)


class DocumentIntelligenceService:
    """Orchestrates document extraction, parsing, chunking, and patient candidate review."""

    @staticmethod
    async def process_document(
        *,
        db: AsyncSession,
        document_id: uuid.UUID,
        patient: PatientProfile,
        storage_root: Path,
        force: bool = False,
        ocr_backend: OcrBackend | None = None,
    ) -> DocumentProcessingJob:
        """
        Execute the Phase 4 document intelligence pipeline on an uploaded document.
        - Enforces patient ownership (403 Forbidden) and active document state (409).
        - SEC-017: Enforces idempotency — returns existing completed job if already
          processed for current pipeline_version (unless force=True), and rejects
          concurrent execution while a job is actively running (409).
        - Stores extracted observations strictly as review_status='candidate'.
        """
        settings = get_settings()
        doc = await DocumentService.get_document(
            db=db, document_id=document_id, patient=patient
        )
        if doc.is_archived:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot process an archived document.",
            )

        file_path = _assert_within_storage_root(Path(doc.file_path), storage_root)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stored document file is not available for processing.",
            )

        # SEC-017: Block concurrent active processing
        running_stmt = select(DocumentProcessingJob).where(
            DocumentProcessingJob.document_id == doc.id,
            DocumentProcessingJob.status == "running",
        )
        running_job = (await db.execute(running_stmt)).scalar_one_or_none()
        if running_job is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document processing is already in progress.",
            )

        # SEC-017: Return existing completed job idempotently when force=False
        pipeline_ver = settings.document_pipeline_version
        base_idempotency_key = f"{doc.id}:{doc.sha256_hash[:16]}:{pipeline_ver}"
        existing_completed = (
            await db.execute(
                select(DocumentProcessingJob)
                .where(
                    DocumentProcessingJob.document_id == doc.id,
                    DocumentProcessingJob.pipeline_version == pipeline_ver,
                    DocumentProcessingJob.status == "completed",
                )
                .order_by(DocumentProcessingJob.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if existing_completed is not None and not force:
            return existing_completed

        # Determine attempt count & unique idempotency key for fresh/forced run
        prev_count = (
            await db.execute(
                select(func.count())
                .select_from(DocumentProcessingJob)
                .where(DocumentProcessingJob.document_id == doc.id)
            )
        ).scalar_one()
        attempt_num = int(prev_count) + 1
        idempotency_key = (
            base_idempotency_key
            if attempt_num == 1
            else f"{base_idempotency_key}:attempt-{attempt_num}-{uuid.uuid4().hex[:6]}"
        )

        job = DocumentProcessingJob(
            id=uuid.uuid4(),
            document_id=doc.id,
            patient_id=patient.id,
            idempotency_key=idempotency_key,
            pipeline_version=pipeline_ver,
            status="running",
            attempt_count=attempt_num,
            started_at=_utc_now(),
        )
        doc.upload_status = "processing"
        doc.processing_error = None
        db.add(job)
        await db.commit()
        await db.refresh(job)

        t0 = time.perf_counter()
        try:
            # Execute CPU-bound PDF/OCR extraction in a worker thread
            extraction = await asyncio.to_thread(
                extract_document_pages,
                file_path,
                doc.mime_type,
                max_pages=settings.max_document_pages,
                ocr_dpi=settings.ocr_dpi,
                min_text_chars_per_page=settings.ocr_min_text_chars_per_page,
                ocr_backend=ocr_backend,
            )

            # Scan each page for SEC-011 prompt injections & collect sanitized text
            all_findings: list[dict[str, Any]] = []
            sanitized_pages: list[tuple[int, str]] = []
            full_sanitized_parts: list[str] = []

            for ext_page in extraction.pages:
                scan = scan_page_text(ext_page.raw_text, ext_page.page_number)
                for f in scan.findings:
                    all_findings.append(
                        {
                            "rule_id": f.rule_id,
                            "page_number": f.page_number,
                            "matched_snippet": f.matched_snippet,
                        }
                    )
                sanitized_pages.append((ext_page.page_number, scan.sanitized_text))
                if scan.sanitized_text.strip():
                    full_sanitized_parts.append(scan.sanitized_text)

            full_sanitized_text = "\n\n".join(full_sanitized_parts)

            # Classify document & extract clinical date
            classification = classify_document(
                full_sanitized_text, filename=doc.original_filename
            )
            extracted_date = extract_clinical_date(full_sanitized_text)
            effective_date = doc.document_date or extracted_date

            # Parse candidate observations page-by-page
            all_candidates: list[CandidateObservation] = []
            for ext_page, (_, sanitized_text) in zip(
                extraction.pages, sanitized_pages, strict=True
            ):
                page_candidates = parse_candidate_observations(
                    sanitized_text,
                    page_number=ext_page.page_number,
                    extraction_method=ext_page.extraction_method,
                    page_confidence=ext_page.ocr_confidence,
                    document_date=effective_date,
                )
                all_candidates.extend(page_candidates)

            # Build page-anchored chunks (Phase 7 RAG ready)
            chunks = build_document_chunks(
                sanitized_pages,
                max_chars=settings.document_chunk_max_chars,
                overlap_chars=settings.document_chunk_overlap_chars,
            )

            # Replace prior embeddings, pages, chunks, and UNCONFIRMED candidates atomically
            # (Confirmed observations are NEVER overwritten or deleted!)
            await db.execute(
                delete(DocumentEmbedding).where(DocumentEmbedding.document_id == doc.id)
            )
            await db.execute(
                delete(DocumentPage).where(DocumentPage.document_id == doc.id)
            )
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
            )
            await db.execute(
                delete(HealthObservation).where(
                    HealthObservation.source_document_id == doc.id,
                    HealthObservation.review_status == "candidate",
                )
            )

            # Persist pages
            for ext_page in extraction.pages:
                db.add(
                    DocumentPage(
                        document_id=doc.id,
                        patient_id=patient.id,
                        page_number=ext_page.page_number,
                        extraction_method=ext_page.extraction_method,
                        raw_text=ext_page.raw_text,
                        ocr_confidence=ext_page.ocr_confidence,
                        char_count=len(ext_page.raw_text),
                        layout_metadata=ext_page.layout_metadata,
                    )
                )

            # Persist chunks (tagged explicitly as untrusted document data)
            for ch in chunks:
                db.add(
                    DocumentChunk(
                        document_id=doc.id,
                        patient_id=patient.id,
                        chunk_index=ch.chunk_index,
                        page_start=ch.page_start,
                        page_end=ch.page_end,
                        content=ch.content,
                        token_estimate=ch.token_estimate,
                        section_heading=ch.section_heading,
                        metadata_json={
                            "trust_level": "untrusted_document_text",
                            "document_type": classification.document_type,
                        },
                    )
                )
            await db.flush()

            # Phase 7: Index patient-scoped RAG embeddings for generated chunks
            rag_index_info = await RagService.index_document_chunks(
                db=db,
                document_id=doc.id,
                patient_id=patient.id,
            )

            # Persist candidate HealthObservations (NEVER confirmed automatically)
            for cand in all_candidates:
                db.add(
                    HealthObservation(
                        patient_id=patient.id,
                        observation_type=cand.observation_type,
                        display_name=cand.display_name,
                        value_raw=cand.value_raw,
                        unit_raw=cand.unit_raw,
                        value_numeric=cand.value_numeric,
                        value_normalized=cand.value_normalized,
                        unit_normalized=cand.unit_normalized,
                        reference_range_text=cand.reference_range_text,
                        abnormality_flag=cand.abnormality_flag,
                        observed_at=_date_to_utc(cand.observed_date),
                        source_type="document_extracted",
                        review_status="candidate",
                        source_document_id=doc.id,
                        source_page=cand.source_page,
                        extraction_method=cand.extraction_method,
                        extraction_confidence=cand.extraction_confidence,
                        provenance_metadata=cand.provenance_metadata,
                        is_archived=False,
                    )
                )

            duration_ms = round((time.perf_counter() - t0) * 1000, 1)
            doc.page_count = extraction.total_pages
            doc.upload_status = "ready"
            if doc.document_date is None and extracted_date is not None:
                doc.document_date = extracted_date
            if doc.document_type == "other" and classification.confidence >= 0.70:
                doc.document_type = classification.document_type

            doc.processing_metadata = {
                "pipeline_version": pipeline_ver,
                "pages_processed": extraction.pages_processed,
                "truncated": extraction.truncated,
                "chunks_count": len(chunks),
                "candidate_observations_count": len(all_candidates),
                "extracted_clinical_date": (
                    extracted_date.isoformat() if extracted_date else None
                ),
                "classification": {
                    "predicted_type": classification.document_type,
                    "confidence": classification.confidence,
                    "matched_signals": classification.matched_signals,
                },
                "security_flags": all_findings,
                "prompt_injection_detected": len(all_findings) > 0,
            }

            job.status = "completed"
            job.completed_at = _utc_now()
            job.metrics_json = {
                "duration_ms": duration_ms,
                "total_pages": extraction.total_pages,
                "pages_processed": extraction.pages_processed,
                "chunks_created": len(chunks),
                "embeddings_indexed": rag_index_info["indexed_chunks"],
                "embedding_model": rag_index_info["embedding_model"],
                "candidates_extracted": len(all_candidates),
                "security_flags_count": len(all_findings),
            }

            await db.commit()
            await db.refresh(job)
            logger.info(
                "document_processed",
                document_id=str(doc.id),
                patient_id=str(patient.id),
                pages=extraction.pages_processed,
                candidates=len(all_candidates),
                security_flags=len(all_findings),
                duration_ms=duration_ms,
            )
            return job

        except HTTPException:
            raise
        except Exception as exc:
            await db.rollback()
            # Persist failure state cleanly on job and document
            job_reloaded = (
                await db.execute(
                    select(DocumentProcessingJob).where(DocumentProcessingJob.id == job.id)
                )
            ).scalar_one_or_none()
            doc_reloaded = (
                await db.execute(select(Document).where(Document.id == doc.id))
            ).scalar_one_or_none()
            if job_reloaded is not None:
                job_reloaded.status = "failed"
                job_reloaded.error_message = str(exc)[:1000]
                job_reloaded.completed_at = _utc_now()
            if doc_reloaded is not None:
                doc_reloaded.upload_status = "failed"
                doc_reloaded.processing_error = str(exc)[:1000]
            await db.commit()
            logger.error(
                "document_processing_failed",
                document_id=str(doc.id),
                error=str(exc),
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Document processing failed.",
            ) from exc

    @staticmethod
    async def get_extraction(
        *,
        db: AsyncSession,
        document_id: uuid.UUID,
        patient: PatientProfile,
    ) -> dict[str, Any]:
        """Return pages, chunks, latest job, classification, security flags, and observations."""
        doc = await DocumentService.get_document(
            db=db, document_id=document_id, patient=patient
        )

        latest_job = (
            await db.execute(
                select(DocumentProcessingJob)
                .where(DocumentProcessingJob.document_id == doc.id)
                .order_by(DocumentProcessingJob.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

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

        observations = list(
            (
                await db.execute(
                    select(HealthObservation)
                    .where(
                        HealthObservation.patient_id == patient.id,
                        HealthObservation.source_document_id == doc.id,
                        HealthObservation.is_archived.is_(False),
                    )
                    .order_by(
                        HealthObservation.source_page.asc(),
                        HealthObservation.created_at.asc(),
                    )
                )
            )
            .scalars()
            .all()
        )

        meta = doc.processing_metadata or {}
        return {
            "document": doc,
            "latest_job": latest_job,
            "pages": pages,
            "chunks_count": len(chunks),
            "chunks": chunks,
            "observations": observations,
            "classification": meta.get("classification"),
            "security_flags": meta.get("security_flags", []),
        }

    @staticmethod
    async def review_candidate(
        *,
        db: AsyncSession,
        document_id: uuid.UUID,
        observation_id: uuid.UUID,
        patient: PatientProfile,
        payload: CandidateReviewRequest,
    ) -> HealthObservation:
        """
        Apply a patient's explicit review decision (confirm, edit_confirm, reject)
        to an extracted candidate HealthObservation with full RecordRevision provenance.
        """
        doc = await DocumentService.get_document(
            db=db, document_id=document_id, patient=patient
        )

        obs = (
            await db.execute(
                select(HealthObservation).where(HealthObservation.id == observation_id)
            )
        ).scalar_one_or_none()
        if obs is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Observation not found.",
            )
        enforce_patient_ownership(obs.patient_id, patient)

        if obs.source_document_id != doc.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Observation does not belong to the specified document.",
            )
        if obs.review_status != "candidate":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Observation has already been finalized ({obs.review_status}).",
            )

        before = _serialize_snapshot(obs, OBSERVATION_FIELDS)

        if payload.action == "reject":
            obs.review_status = "rejected"
            obs.is_archived = True
            after = _serialize_snapshot(obs, OBSERVATION_FIELDS)
            await HealthRecordsService._record_revision(
                db,
                patient_id=patient.id,
                user_id=patient.user_id,
                entity_type="observation",
                entity_id=obs.id,
                action="archived",
                previous_data=before,
                new_data=after,
                reason=payload.reason or "Rejected extracted candidate during document review",
            )
        else:
            if payload.action == "edit_confirm":
                editable = payload.model_dump(
                    exclude={"action", "reason"}, exclude_unset=True
                )
                for field, value in editable.items():
                    setattr(obs, field, value)
                if "value_raw" in editable and editable["value_raw"] is not None:
                    obs.value_numeric = _try_parse_float(obs.value_raw)
                    obs.value_normalized = obs.value_numeric

            obs.review_status = "confirmed"
            obs.source_type = "patient_confirmed"
            after = _serialize_snapshot(obs, OBSERVATION_FIELDS)

            await HealthRecordsService._record_revision(
                db,
                patient_id=patient.id,
                user_id=patient.user_id,
                entity_type="observation",
                entity_id=obs.id,
                action="corrected" if payload.action == "edit_confirm" else "created",
                previous_data=before,
                new_data=after,
                reason=(
                    payload.reason
                    or (
                        "Edited and confirmed extracted observation"
                        if payload.action == "edit_confirm"
                        else "Confirmed extracted observation from document"
                    )
                ),
            )

            unit_part = f" {obs.unit_raw}" if obs.unit_raw else ""
            db.add(
                HealthEvent(
                    patient_id=patient.id,
                    event_category="observation",
                    title=f"{obs.display_name}: {obs.value_raw}{unit_part}",
                    summary=(
                        f"Confirmed from document '{doc.title}' (page {obs.source_page or 1})"
                    ),
                    event_occurred_at=obs.observed_at,
                    source_type="patient_confirmed",
                    review_status="confirmed",
                    related_entity_type="observation",
                    related_entity_id=obs.id,
                    metadata_json={
                        "source_document_id": str(doc.id),
                        "source_page": obs.source_page,
                        "abnormality_flag": obs.abnormality_flag,
                    },
                )
            )

        await db.flush()

        # If no candidate observations remain for this document, mark document reviewed
        remaining_candidates = (
            await db.execute(
                select(func.count())
                .select_from(HealthObservation)
                .where(
                    HealthObservation.patient_id == patient.id,
                    HealthObservation.source_document_id == doc.id,
                    HealthObservation.review_status == "candidate",
                    HealthObservation.is_archived.is_(False),
                )
            )
        ).scalar_one()
        if int(remaining_candidates) == 0:
            doc.review_status = "reviewed"

        await db.commit()
        await db.refresh(obs)
        return obs

    @staticmethod
    async def list_pending_candidates(
        *,
        db: AsyncSession,
        patient: PatientProfile,
    ) -> list[HealthObservation]:
        """List all pending candidate observations across all documents for a patient."""
        rows = (
            await db.execute(
                select(HealthObservation)
                .where(
                    HealthObservation.patient_id == patient.id,
                    HealthObservation.review_status == "candidate",
                    HealthObservation.is_archived.is_(False),
                )
                .order_by(HealthObservation.created_at.desc())
            )
        ).scalars().all()
        return list(rows)
