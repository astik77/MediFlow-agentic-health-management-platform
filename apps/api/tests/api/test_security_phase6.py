"""
Phase 6 Security & Clinical Safety Tests.
Verifies:
- SEC-001/002: Cross-patient conversation & proposal isolation (403 Forbidden)
- SEC-004: Unauthenticated rejection (401) across all conversation endpoints
- SEC-013: Hallucinated foreign patient_id in assistant output handled safely
- AIR-004: Deterministic emergency escalation & prescribing/dosage refusal over HTTP
"""
from __future__ import annotations

import json
import uuid

import pytest
from httpx import AsyncClient

from mediflow.ai.providers.mock import MockAIProvider
from mediflow.ai.providers.router import ProviderRouter
from mediflow.core.dependencies import SESSION_COOKIE_NAME
from mediflow.modules.auth.models import User
from mediflow.modules.patients.models import PatientProfile


@pytest.mark.asyncio
async def test_sec004_unauthenticated_conversations_rejected(
    test_client: AsyncClient,
) -> None:
    """SEC-004: Unauthenticated requests to /api/v1/conversations/* return 401."""
    cid = uuid.uuid4()
    mid = uuid.uuid4()
    assert (await test_client.get("/api/v1/conversations")).status_code == 401
    assert (await test_client.post("/api/v1/conversations", json={})).status_code == 401
    assert (await test_client.get(f"/api/v1/conversations/{cid}")).status_code == 401
    assert (
        await test_client.post(f"/api/v1/conversations/{cid}/messages", json={"content": "hi"})
    ).status_code == 401
    assert (
        await test_client.post(
            f"/api/v1/conversations/{cid}/messages/{mid}/proposal",
            json={"decision": "accept"},
        )
    ).status_code == 401


@pytest.mark.asyncio
async def test_sec001_002_cross_patient_conversation_isolation(
    test_client: AsyncClient,
    test_patient: tuple[User, PatientProfile, str],
    second_patient: tuple[User, PatientProfile, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-001/002: Patient B cannot view, message, archive, or confirm Patient A's chat."""
    monkeypatch.setattr(
        "mediflow.ai.agents.health_assistant._assistant_router",
        lambda: ProviderRouter(override_providers={"ollama": MockAIProvider()}),
    )
    _, _, token_a = test_patient
    _, _, token_b = second_patient

    test_client.cookies.set(SESSION_COOKIE_NAME, token_a)
    conv_id = (await test_client.post("/api/v1/conversations", json={})).json()["id"]
    turn = (
        await test_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"content": "I have had a mild headache today."},
        )
    ).json()
    asst_msg_id = turn["assistant_message"]["id"]

    # Switch to Patient B
    test_client.cookies.set(SESSION_COOKIE_NAME, token_b)

    assert (await test_client.get("/api/v1/conversations")).json() == []
    assert (await test_client.get(f"/api/v1/conversations/{conv_id}")).status_code == 403
    assert (
        await test_client.post(
            f"/api/v1/conversations/{conv_id}/messages", json={"content": "snoop"}
        )
    ).status_code == 403
    assert (
        await test_client.post(
            f"/api/v1/conversations/{conv_id}/messages/{asst_msg_id}/proposal",
            json={"decision": "accept"},
        )
    ).status_code == 403
    assert (await test_client.delete(f"/api/v1/conversations/{conv_id}")).status_code == 403


@pytest.mark.asyncio
async def test_air004_emergency_and_boundary_safety_over_http(
    authenticated_client: AsyncClient,
) -> None:
    """AIR-004: Emergency red flags and prescribing/dosage prompts trigger deterministic safety."""
    conv_id = (await authenticated_client.post("/api/v1/conversations", json={})).json()["id"]

    # Emergency red flag bypasses LLM completely
    em = await authenticated_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "I have severe chest pain and shortness of breath right now!"},
    )
    assert em.status_code == 201
    asst_em = em.json()["assistant_message"]
    assert asst_em["safety_level"] == "emergency_escalation"
    assert asst_em["metadata_json"]["bypassed_llm"] is True
    assert "112" in asst_em["content"]

    # Dosage change refusal
    rx = await authenticated_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Should I double my metformin dose tonight?"},
    )
    assert rx.status_code == 201
    asst_rx = rx.json()["assistant_message"]
    assert asst_rx["safety_level"] == "boundary_refusal"
    assert "cannot recommend" in asst_rx["content"].lower()


@pytest.mark.asyncio
async def test_sec013_assistant_rejects_hallucinated_foreign_patient_id(
    authenticated_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-013: Hallucinated foreign patient_id in assistant JSON is intercepted safely."""
    bad_json = json.dumps(
        {
            "patient_id": str(uuid.uuid4()),
            "reply": "Foreign patient leaked reply.",
            "clarifying_questions": [],
            "cited_record_ids": [],
            "proposed_symptom": None,
            "informational_disclaimer": "Informational only; not medical advice.",
        }
    )
    monkeypatch.setattr(
        "mediflow.ai.agents.health_assistant._assistant_router",
        lambda: ProviderRouter(
            override_providers={"ollama": MockAIProvider(response_sequence=[bad_json])}
        ),
    )

    conv_id = (await authenticated_client.post("/api/v1/conversations", json={})).json()["id"]
    res = await authenticated_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Summarize my recent labs."},
    )
    assert res.status_code == 201
    asst = res.json()["assistant_message"]
    assert asst["safety_level"] == "boundary_refusal"
    assert asst["metadata_json"]["error_code"] == "sec013_patient_id_mismatch"
    assert "Foreign patient leaked" not in asst["content"]
