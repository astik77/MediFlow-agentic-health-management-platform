"""
Phase 6 API Integration Tests — AI Health Assistant & Conversations.
Covers conversation CRUD, multi-turn messaging grounded in patient history,
symptom clarification, proposal acceptance/dismissal into patient_symptoms,
soft-archive, and graceful offline Ollama fallback.
"""
from __future__ import annotations

import httpx
import pytest
from httpx import AsyncClient

from mediflow.ai.providers.mock import MockAIProvider
from mediflow.ai.providers.ollama import OllamaProvider
from mediflow.ai.providers.router import ProviderRouter


@pytest.mark.asyncio
async def test_conversation_lifecycle_grounded_reply_and_symptom_proposal(
    authenticated_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CONV-001: Full conversation lifecycle + proposal-only symptom confirmation."""
    monkeypatch.setattr(
        "mediflow.ai.agents.health_assistant._assistant_router",
        lambda: ProviderRouter(override_providers={"ollama": MockAIProvider()}),
    )

    # Seed patient record so context tools ground the conversation
    await authenticated_client.post(
        "/api/v1/health-records/conditions",
        json={"name": "Hypertension", "status": "active"},
    )
    await authenticated_client.post(
        "/api/v1/health-records/observations",
        json={
            "display_name": "Hemoglobin",
            "value_raw": "13.4",
            "unit_raw": "g/dL",
            "reference_range_text": "12.0 - 16.0",
        },
    )

    # Create conversation
    c_res = await authenticated_client.post("/api/v1/conversations", json={})
    assert c_res.status_code == 201
    conv_id = c_res.json()["id"]

    # Send message mentioning a headache
    m1 = await authenticated_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={
            "content": "I have had a dull headache since morning and wanted to check my history."
        },
    )
    assert m1.status_code == 201
    turn = m1.json()
    assert turn["conversation"]["title"].startswith("I have had a dull headache")
    asst = turn["assistant_message"]
    assert asst["role"] == "assistant"
    assert asst["safety_level"] == "normal"
    assert len(asst["clarifying_questions_json"]) >= 1
    assert asst["cited_records_json"] is not None
    assert len(asst["cited_records_json"]) >= 1

    # Symptom proposal must remain pending (NOT silently saved yet)
    proposal = asst["proposed_action_json"]
    assert proposal is not None
    assert proposal["status"] == "pending"
    assert proposal["payload"]["name"] == "Headache"
    assert (await authenticated_client.get("/api/v1/health-records/symptoms")).json() == []

    # Patient explicitly accepts the proposed symptom draft
    acc = await authenticated_client.post(
        f"/api/v1/conversations/{conv_id}/messages/{asst['id']}/proposal",
        json={"decision": "accept", "severity": "mild"},
    )
    assert acc.status_code == 200
    assert acc.json()["proposed_action_json"]["status"] == "saved"
    saved_sym_id = acc.json()["proposed_action_json"]["saved_entity_id"]

    # Verify PatientSymptom created with ai_proposed provenance + RecordRevision
    syms = (await authenticated_client.get("/api/v1/health-records/symptoms")).json()
    assert len(syms) == 1
    assert syms[0]["id"] == saved_sym_id
    assert syms[0]["source_type"] == "ai_proposed"
    assert syms[0]["review_status"] == "confirmed"
    assert syms[0]["severity"] == "mild"

    # Double resolution returns 409 Conflict
    dup = await authenticated_client.post(
        f"/api/v1/conversations/{conv_id}/messages/{asst['id']}/proposal",
        json={"decision": "dismiss"},
    )
    assert dup.status_code == 409

    # Fetch conversation detail -> both messages present
    detail = await authenticated_client.get(f"/api/v1/conversations/{conv_id}")
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 2

    # Archive conversation -> excluded from active list & blocks further posts
    arch = await authenticated_client.delete(f"/api/v1/conversations/{conv_id}")
    assert arch.status_code == 200
    assert arch.json()["is_archived"] is True
    assert (await authenticated_client.get("/api/v1/conversations")).json() == []
    blocked_post = await authenticated_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Another message"},
    )
    assert blocked_post.status_code == 409


@pytest.mark.asyncio
async def test_assistant_graceful_fallback_when_ollama_offline(
    authenticated_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CONV-002: When Ollama is offline, assistant degrades cleanly without HTTP 500."""

    def offline_handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    offline_ollama = OllamaProvider(transport=httpx.MockTransport(offline_handler))
    monkeypatch.setattr(
        "mediflow.ai.agents.health_assistant._assistant_router",
        lambda: ProviderRouter(override_providers={"ollama": offline_ollama}),
    )

    conv_id = (await authenticated_client.post("/api/v1/conversations", json={})).json()["id"]
    res = await authenticated_client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "I have had mild fatigue today, can you check my history?"},
    )
    assert res.status_code == 201
    asst = res.json()["assistant_message"]
    assert asst["metadata_json"]["provider"] == "offline_fallback"
    assert asst["proposed_action_json"]["payload"]["name"] == "Fatigue"

    # Dismissing the proposal marks it dismissed without creating a symptom record
    dis = await authenticated_client.post(
        f"/api/v1/conversations/{conv_id}/messages/{asst['id']}/proposal",
        json={"decision": "dismiss"},
    )
    assert dis.status_code == 200
    assert dis.json()["proposed_action_json"]["status"] == "dismissed"
    assert (await authenticated_client.get("/api/v1/health-records/symptoms")).json() == []
