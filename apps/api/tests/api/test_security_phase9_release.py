"""
Phase 9 Security Hardening, Patient Data Portability & Cascading Erasure Tests.
Verifies HTTP security headers, Cache-Control: no-store, portable JSON export
(zero cross-patient or internal secret leakage), re-authenticated account deletion
with physical disk + full DB erasure, and post-deletion session invalidation.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.models import AIInvocationLog
from mediflow.core.config import Settings
from mediflow.core.dependencies import SESSION_COOKIE_NAME
from mediflow.modules.analytics.models import HealthSummary
from mediflow.modules.auth.models import Session, User
from mediflow.modules.conversations.models import Conversation, Message
from mediflow.modules.documents.models import (
    Document,
    DocumentChunk,
    DocumentEmbedding,
    DocumentPage,
    DocumentProcessingJob,
)
from mediflow.modules.health_records.models import (
    HealthObservation,
    PatientAllergy,
    PatientCondition,
    PatientSymptom,
)
from mediflow.modules.patients import service as patient_service_module
from mediflow.modules.patients.models import PatientProfile


@pytest.mark.asyncio
async def test_security_headers_and_no_store_on_api_routes(
    authenticated_client: AsyncClient,
) -> None:
    root_resp = await authenticated_client.get("/health")
    assert root_resp.status_code == 200
    assert root_resp.headers.get("x-content-type-options") == "nosniff"
    assert root_resp.headers.get("x-frame-options") == "DENY"
    assert root_resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in (root_resp.headers.get("permissions-policy") or "")

    api_resp = await authenticated_client.get("/api/v1/patients/profile")
    assert api_resp.status_code == 200
    assert api_resp.headers.get("x-content-type-options") == "nosniff"
    assert api_resp.headers.get("x-frame-options") == "DENY"
    assert api_resp.headers.get("cache-control") == "no-store"
    assert api_resp.headers.get("pragma") == "no-cache"


@pytest.mark.asyncio
async def test_export_and_delete_require_authentication_sec004(
    test_client: AsyncClient,
) -> None:
    assert (await test_client.get("/api/v1/patients/export")).status_code == 401
    del_resp = await test_client.request(
        "DELETE",
        "/api/v1/patients/account",
        json={"password": "SecurePassword123!", "confirm_text": "DELETE MY ACCOUNT"},
    )
    assert del_resp.status_code == 401


@pytest.mark.asyncio
async def test_patient_export_completeness_isolation_and_no_secret_leakage(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    test_patient: tuple[User, PatientProfile, str],
    second_patient: tuple[User, PatientProfile, str],
) -> None:
    user_a, patient_a, _ = test_patient
    _, patient_b, _ = second_patient
    now = datetime.now(UTC)

    # Seed Patient A records
    db_session.add(
        PatientCondition(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            name="Hypertension",
            status="active",
        )
    )
    db_session.add(
        PatientAllergy(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            allergen="Sulfa Drugs",
            category="medication",
        )
    )
    db_session.add(
        PatientSymptom(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            name="Mild Headache",
            severity="mild",
        )
    )
    db_session.add(
        HealthObservation(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            observation_type="lab_result",
            display_name="HbA1c",
            value_raw="5.9",
            unit_raw="%",
            value_numeric=5.9,
            observed_at=now,
        )
    )
    db_session.add(
        Document(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            uploader_user_id=user_a.id,
            original_filename="annual_lab.pdf",
            stored_filename="secret-uuid-stored-name.pdf",
            file_path="/var/private/secret/annual_lab.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            sha256_hash="b" * 64,
            document_type="lab_report",
            title="Annual Lab Report",
        )
    )
    conv = Conversation(id=uuid.uuid4(), patient_id=patient_a.id, title="Lab Review")
    db_session.add(conv)
    await db_session.flush()
    db_session.add(
        Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            patient_id=patient_a.id,
            role="user",
            content="What was my HbA1c?",
        )
    )
    db_session.add(
        HealthSummary(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            window_days=7,
            period_start=now - timedelta(days=7),
            period_end=now,
            headline="7-Day Summary",
            summary_text="All metrics reviewed.",
            highlights_json=["HbA1c 5.9%"],
            notable_trends_json=[],
            questions_for_doctor_json=["Next test date?"],
            metrics_snapshot_json={"observations_in_window": 1},
            generation_mode="deterministic_fallback",
        )
    )

    # Seed Patient B confidential data (must NEVER leak into Patient A's export)
    db_session.add(
        PatientCondition(
            id=uuid.uuid4(),
            patient_id=patient_b.id,
            name="CONFIDENTIAL_PATIENT_B_DIAGNOSIS",
            status="active",
        )
    )
    await db_session.commit()

    resp = await authenticated_client.get("/api/v1/patients/export")
    assert resp.status_code == 200
    data = resp.json()

    assert data["export_version"] == "1.0.0"
    assert data["account_email"] == user_a.email
    assert data["profile"]["id"] == str(patient_a.id)
    assert data["counts"]["conditions"] == 1
    assert data["counts"]["allergies"] == 1
    assert data["counts"]["symptoms"] == 1
    assert data["counts"]["observations"] == 1
    assert data["counts"]["documents"] == 1
    assert data["counts"]["conversations"] == 1
    assert data["counts"]["messages"] == 1
    assert data["counts"]["health_summaries"] == 1
    assert len(data["conversations"][0]["messages"]) == 1

    # Strictly zero foreign data and zero internal secrets / server paths
    serialized = json.dumps(data)
    assert "CONFIDENTIAL_PATIENT_B_DIAGNOSIS" not in serialized
    assert "/var/private/secret/annual_lab.pdf" not in serialized
    assert "secret-uuid-stored-name.pdf" not in serialized
    assert "file_path" not in serialized
    assert "stored_filename" not in serialized
    assert "password_hash" not in serialized
    assert "session_token_hash" not in serialized


@pytest.mark.asyncio
async def test_account_deletion_guards_wrong_confirm_and_wrong_password(
    authenticated_client: AsyncClient,
) -> None:
    bad_confirm = await authenticated_client.request(
        "DELETE",
        "/api/v1/patients/account",
        json={"password": "SecurePassword123!", "confirm_text": "delete"},
    )
    assert bad_confirm.status_code == 400

    bad_pw = await authenticated_client.request(
        "DELETE",
        "/api/v1/patients/account",
        json={"password": "WrongPassword999!", "confirm_text": "DELETE MY ACCOUNT"},
    )
    assert bad_pw.status_code == 403

    # Account must still be active and accessible
    assert (await authenticated_client.get("/api/v1/patients/profile")).status_code == 200


@pytest.mark.asyncio
async def test_account_deletion_erases_disk_files_all_tables_and_preserves_other_patients(
    test_client: AsyncClient,
    db_session: AsyncSession,
    test_patient: tuple[User, PatientProfile, str],
    second_patient: tuple[User, PatientProfile, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_a, patient_a, token_a = test_patient
    user_b, patient_b, token_b = second_patient
    now = datetime.now(UTC)

    storage_root = tmp_path / "private_uploads"
    dir_a = storage_root / str(patient_a.id)
    dir_b = storage_root / str(patient_b.id)
    dir_a.mkdir(parents=True)
    dir_b.mkdir(parents=True)

    file_a = dir_a / "a_report.pdf"
    file_b = dir_b / "b_report.pdf"
    file_a.write_bytes(b"%PDF-1.4 patient A file")
    file_b.write_bytes(b"%PDF-1.4 patient B file")

    monkeypatch.setattr(
        patient_service_module,
        "get_settings",
        lambda: Settings(upload_dir=str(storage_root)),
    )

    # Seed Patient A across document/RAG/health/conversation/analytics/AI tables
    doc_a = Document(
        id=uuid.uuid4(),
        patient_id=patient_a.id,
        uploader_user_id=user_a.id,
        original_filename="a.pdf",
        stored_filename="a_report.pdf",
        file_path=str(file_a),
        mime_type="application/pdf",
        file_size_bytes=23,
        sha256_hash="c" * 64,
        document_type="lab_report",
        title="Patient A Doc",
    )
    db_session.add(doc_a)
    await db_session.flush()

    db_session.add(
        DocumentPage(
            id=uuid.uuid4(),
            document_id=doc_a.id,
            patient_id=patient_a.id,
            page_number=1,
            extraction_method="pymupdf_text",
            raw_text="HbA1c 6.1%",
            char_count=10,
        )
    )
    chunk_a = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_a.id,
        patient_id=patient_a.id,
        chunk_index=0,
        page_start=1,
        page_end=1,
        content="HbA1c 6.1%",
        token_estimate=3,
    )
    db_session.add(chunk_a)
    await db_session.flush()

    db_session.add(
        DocumentEmbedding(
            id=uuid.uuid4(),
            chunk_id=chunk_a.id,
            document_id=doc_a.id,
            patient_id=patient_a.id,
            embedding_model="local-hash-256-v1",
            dimensions=4,
            embedding_vector=[0.5, 0.5, 0.5, 0.5],
            content_hash="d" * 64,
        )
    )
    db_session.add(
        DocumentProcessingJob(
            id=uuid.uuid4(),
            document_id=doc_a.id,
            patient_id=patient_a.id,
            idempotency_key=f"key-{doc_a.id}",
            pipeline_version="phase4-v1",
            status="completed",
        )
    )
    db_session.add(
        PatientCondition(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            name="Condition A",
        )
    )
    db_session.add(
        AIInvocationLog(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            provider="ollama",
            model_name="qwen2.5:1.5b",
            prompt_id="doc_summary",
            prompt_version="1.0.0",
            task_type="document_summary",
            status="succeeded",
        )
    )

    # Seed Patient B document + condition (must remain 100% untouched)
    doc_b = Document(
        id=uuid.uuid4(),
        patient_id=patient_b.id,
        uploader_user_id=user_b.id,
        original_filename="b.pdf",
        stored_filename="b_report.pdf",
        file_path=str(file_b),
        mime_type="application/pdf",
        file_size_bytes=23,
        sha256_hash="e" * 64,
        document_type="lab_report",
        title="Patient B Doc",
    )
    db_session.add(doc_b)
    db_session.add(
        PatientCondition(
            id=uuid.uuid4(),
            patient_id=patient_b.id,
            name="Condition B",
        )
    )
    db_session.add(
        HealthSummary(
            id=uuid.uuid4(),
            patient_id=patient_a.id,
            window_days=7,
            period_start=now - timedelta(days=7),
            period_end=now,
            headline="Summary A",
            summary_text="Body A",
            highlights_json=[],
            notable_trends_json=[],
            questions_for_doctor_json=[],
            metrics_snapshot_json={},
            generation_mode="deterministic_fallback",
        )
    )
    await db_session.commit()

    # Patient A deletes account
    test_client.cookies.set(SESSION_COOKIE_NAME, token_a)
    del_resp = await test_client.request(
        "DELETE",
        "/api/v1/patients/account",
        json={"password": "SecurePassword123!", "confirm_text": "DELETE MY ACCOUNT"},
    )
    assert del_resp.status_code == 200
    receipt = del_resp.json()
    assert receipt["deleted"] is True
    assert receipt["files_removed"] == 1

    # Physical file for Patient A erased; Patient B file intact
    assert not file_a.exists()
    assert file_b.exists()

    # Zero DB rows remain for Patient A
    assert (
        await db_session.execute(select(User).where(User.id == user_a.id))
    ).scalar_one_or_none() is None
    assert (
        await db_session.execute(
            select(PatientProfile).where(PatientProfile.id == patient_a.id)
        )
    ).scalar_one_or_none() is None
    assert (
        await db_session.execute(select(Session).where(Session.user_id == user_a.id))
    ).scalars().all() == []
    assert (
        await db_session.execute(
            select(Document).where(Document.patient_id == patient_a.id)
        )
    ).scalars().all() == []
    assert (
        await db_session.execute(
            select(DocumentEmbedding).where(DocumentEmbedding.patient_id == patient_a.id)
        )
    ).scalars().all() == []
    assert (
        await db_session.execute(
            select(HealthSummary).where(HealthSummary.patient_id == patient_a.id)
        )
    ).scalars().all() == []
    assert (
        await db_session.execute(
            select(AIInvocationLog).where(AIInvocationLog.patient_id == patient_a.id)
        )
    ).scalars().all() == []

    # Old Patient A token is immediately rejected
    test_client.cookies.set(SESSION_COOKIE_NAME, token_a)
    me_a = await test_client.get("/api/v1/auth/me")
    assert me_a.status_code == 200
    assert me_a.json()["authenticated"] is False
    assert (await test_client.get("/api/v1/patients/profile")).status_code == 401

    # Patient B remains completely intact and operational
    test_client.cookies.set(SESSION_COOKIE_NAME, token_b)
    prof_b = await test_client.get("/api/v1/patients/profile")
    assert prof_b.status_code == 200
    assert prof_b.json()["id"] == str(patient_b.id)
    exp_b = await test_client.get("/api/v1/patients/export")
    assert exp_b.status_code == 200
    assert exp_b.json()["counts"]["documents"] == 1
    assert exp_b.json()["counts"]["conditions"] == 1
