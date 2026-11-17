"""
Patient-Scoped AI Health Assistant Agent (Phase 6).

Combines:
- Deterministic clinical safety triage & emergency escalation (AIR-004 = 100%)
- SEC-012 allowlisted read-only & proposal-only patient-scoped tools
- Local-first Ollama inference via SEC-014 Privacy Firewall
- Pydantic v2 structured output validation & SEC-013 patient_id verification
- Graceful record-grounded offline fallback when Ollama is not running
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.agents.tools import AgentToolRegistry
from mediflow.ai.models import AIInvocationLog
from mediflow.ai.prompts import get_prompt, wrap_untrusted_document_text
from mediflow.ai.providers.base import (
    AIProviderError,
    GenerationRequest,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from mediflow.ai.providers.router import ProviderRouter
from mediflow.ai.safety.clinical_safety import (
    INFORMATIONAL_DISCLAIMER,
    SafetyLevel,
    enforce_safe_assistant_reply,
    evaluate_user_message_safety,
)
from mediflow.ai.safety.structured_output import (
    PatientIdentityMismatchError,
    StructuredOutputError,
    generate_structured_output,
)
from mediflow.core.config import get_settings
from mediflow.core.logging import get_logger
from mediflow.modules.patients.models import PatientProfile

logger = get_logger(__name__)

_COMMON_SYMPTOM_HINTS: list[tuple[str, str | None]] = [
    ("headache", "head"),
    ("migraine", "head"),
    ("fever", None),
    ("fatigue", None),
    ("tiredness", None),
    ("cough", "chest/throat"),
    ("sore throat", "throat"),
    ("nausea", "stomach"),
    ("stomach ache", "abdomen"),
    ("abdominal pain", "abdomen"),
    ("dizziness", "head"),
    ("joint pain", "joints"),
    ("back pain", "back"),
    ("rash", "skin"),
]


class ProposedSymptomDraft(BaseModel):
    """Proposal-only symptom draft requiring explicit patient confirmation."""

    name: str = Field(..., min_length=1, max_length=255)
    severity: Literal["mild", "moderate", "severe"] = "moderate"
    body_location: str | None = Field(None, max_length=150)
    frequency: str | None = Field(None, max_length=100)
    notes: str | None = Field(None, max_length=500)


class AssistantTurnOutput(BaseModel):
    """Strictly validated structured output for an AI Health Assistant turn."""

    patient_id: uuid.UUID
    reply: str = Field(..., min_length=5, max_length=4000)
    clarifying_questions: list[str] = Field(default_factory=list, max_length=5)
    cited_record_ids: list[str] = Field(default_factory=list, max_length=12)
    proposed_symptom: ProposedSymptomDraft | None = None
    informational_disclaimer: str = Field(
        default=INFORMATIONAL_DISCLAIMER, min_length=10, max_length=500
    )


@dataclass(slots=True)
class AssistantTurnResult:
    """Normalized turn output ready for persistence in the messages table."""

    content: str
    safety_level: SafetyLevel
    cited_records: list[dict[str, str]] = field(default_factory=list)
    clarifying_questions: list[str] = field(default_factory=list)
    proposed_action: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _assistant_router() -> ProviderRouter:
    """Monkeypatchable router factory for tests."""
    return ProviderRouter(settings=get_settings())


def _detect_symptom_hint(message: str) -> tuple[str, str | None] | None:
    low = message.lower()
    for term, loc in _COMMON_SYMPTOM_HINTS:
        if re.search(rf"\b{re.escape(term)}\b", low):
            return term.title(), loc
    return None


class HealthAssistantAgent:
    """Patient-scoped conversational health assistant backed by allowlisted tools."""

    @staticmethod
    async def _gather_patient_context(
        db: AsyncSession,
        patient: PatientProfile,
        *,
        user_query: str = "",
    ) -> tuple[str, dict[str, dict[str, str]], dict[str, Any]]:
        """
        Gather authenticated patient's longitudinal health context strictly via
        SEC-012 allowlisted read-only tools.
        Returns (formatted_context_text, valid_citation_lookup_by_id, raw_bundle).
        """
        profile = await AgentToolRegistry.execute(
            tool_name="get_patient_profile_summary", db=db, patient=patient
        )
        conds = await AgentToolRegistry.execute(
            tool_name="list_active_conditions", db=db, patient=patient
        )
        allergies = await AgentToolRegistry.execute(
            tool_name="list_allergies", db=db, patient=patient
        )
        symptoms = await AgentToolRegistry.execute(
            tool_name="list_recent_symptoms", db=db, patient=patient
        )
        obs = await AgentToolRegistry.execute(
            tool_name="list_recent_observations", db=db, patient=patient
        )
        docs = await AgentToolRegistry.execute(
            tool_name="list_recent_documents", db=db, patient=patient
        )

        citation_index: dict[str, dict[str, str]] = {}
        sections: list[str] = []

        # Baseline profile
        prof_bits = [
            f"Sex: {profile.get('biological_sex') or 'unspecified'}",
            f"Blood Group: {profile.get('blood_group') or 'unspecified'}",
        ]
        if profile.get("date_of_birth"):
            prof_bits.append(f"DOB: {profile['date_of_birth']}")
        sections.append("Profile: " + ", ".join(prof_bits))

        # Conditions
        if conds["conditions"]:
            lines = []
            for c in conds["conditions"]:
                citation_index[c["id"]] = {
                    "entity_type": "condition",
                    "entity_id": c["id"],
                    "label": f"Condition: {c['name']} ({c['status']})",
                }
                lines.append(f"- [{c['id']}] {c['name']} (status={c['status']})")
            sections.append("Conditions:\n" + "\n".join(lines))

        # Allergies
        if allergies["allergies"]:
            lines = []
            for a in allergies["allergies"]:
                citation_index[a["id"]] = {
                    "entity_type": "allergy",
                    "entity_id": a["id"],
                    "label": f"Allergy: {a['allergen']} ({a['severity']})",
                }
                lines.append(
                    f"- [{a['id']}] {a['allergen']} ({a['severity']}, reaction={a['reaction']})"
                )
            sections.append("Allergies:\n" + "\n".join(lines))

        # Symptoms
        if symptoms["symptoms"]:
            lines = []
            for s in symptoms["symptoms"]:
                citation_index[s["id"]] = {
                    "entity_type": "symptom",
                    "entity_id": s["id"],
                    "label": f"Symptom: {s['name']} ({s['severity']})",
                }
                lines.append(
                    f"- [{s['id']}] {s['name']} (severity={s['severity']}, status={s['status']})"
                )
            sections.append("Recent Symptoms:\n" + "\n".join(lines))

        # Confirmed observations
        if obs["observations"]:
            lines = []
            for o in obs["observations"]:
                unit = f" {o['unit_raw']}" if o["unit_raw"] else ""
                flag = f" [{o['abnormality_flag']}]" if o["abnormality_flag"] else ""
                citation_index[o["id"]] = {
                    "entity_type": "observation",
                    "entity_id": o["id"],
                    "label": f"{o['display_name']}: {o['value_raw']}{unit}",
                }
                lines.append(
                    f"- [{o['id']}] {o['display_name']}: {o['value_raw']}{unit}"
                    f" (ref={o['reference_range_text']}){flag}"
                )
            sections.append("Confirmed Observations:\n" + "\n".join(lines))

        # Documents
        if docs["documents"]:
            lines = []
            for d in docs["documents"]:
                citation_index[d["id"]] = {
                    "entity_type": "document",
                    "entity_id": d["id"],
                    "label": f"Document: {d['title']}",
                }
                lines.append(
                    f"- [{d['id']}] {d['title']} ({d['document_type']}, date={d['document_date']})"
                )
            sections.append("Uploaded Documents:\n" + "\n".join(lines))

        # Phase 7: Hybrid Patient-Specific RAG Passages (wrapped as SEC-011 untrusted data)
        rag_hits: list[dict[str, Any]] = []
        if user_query.strip():
            rag_res = await AgentToolRegistry.execute(
                tool_name="search_patient_documents",
                db=db,
                patient=patient,
                arguments={"query": user_query, "top_k": 3},
            )
            rag_hits = rag_res.get("hits", [])
            if rag_hits:
                rag_lines = []
                for h in rag_hits:
                    page_label = (
                        f"p. {h['page_start']}"
                        if h["page_start"] == h["page_end"]
                        else f"pp. {h['page_start']}-{h['page_end']}"
                    )
                    citation_index[h["chunk_id"]] = {
                        "entity_type": "document_chunk",
                        "entity_id": h["document_id"],
                        "label": f"{h['document_title']} ({page_label})",
                    }
                    rag_lines.append(
                        f"- [{h['chunk_id']}] {h['document_title']} ({page_label}): {h['snippet']}"
                    )
                sections.append(
                    "Relevant Document Excerpts (UNTRUSTED DATA ONLY):\n"
                    + wrap_untrusted_document_text("\n".join(rag_lines), max_chars=2500)
                )

        bundle = {
            "profile": profile,
            "conditions": conds["conditions"],
            "allergies": allergies["allergies"],
            "symptoms": symptoms["symptoms"],
            "observations": obs["observations"],
            "documents": docs["documents"],
            "rag_hits": rag_hits,
        }
        return "\n\n".join(sections), citation_index, bundle

    @staticmethod
    def _match_relevant_citations(
        user_message: str, citation_index: dict[str, dict[str, str]]
    ) -> list[dict[str, str]]:
        """Deterministically surface matching patient records for grounding & offline fallback."""
        low = user_message.lower()
        hits: list[dict[str, str]] = []
        for item in citation_index.values():
            label_words = [
                w for w in re.findall(r"[a-z0-9]+", item["label"].lower()) if len(w) >= 4
            ]
            if any(w in low for w in label_words):
                hits.append(item)
        # If user asks a broad history summary question, cite top records
        if not hits and any(
            k in low
            for k in ("history", "summary", "records", "labs", "results", "allergies", "conditions")
        ):
            hits = list(citation_index.values())[:5]
        return hits[:6]

    @staticmethod
    async def respond(
        *,
        db: AsyncSession,
        patient: PatientProfile,
        user_message: str,
        history_turns: list[tuple[str, str]],
        router: ProviderRouter | None = None,
    ) -> AssistantTurnResult:
        """Execute one full safety-checked, context-grounded AI Health Assistant turn."""
        cfg = get_settings()
        prompt = get_prompt("health_assistant")

        # 1. Deterministic Pre-LLM Clinical Safety Triage (AIR-004 = 100%)
        safety = evaluate_user_message_safety(user_message)
        if safety.safety_level == "emergency_escalation" and safety.override_reply:
            db.add(
                AIInvocationLog(
                    patient_id=patient.id,
                    provider="deterministic_safety",
                    model_name="clinical_safety_v1",
                    prompt_id=prompt.prompt_id,
                    prompt_version=prompt.version,
                    task_type="emergency_escalation",
                    status="succeeded",
                    schema_valid=True,
                    is_synthetic=False,
                )
            )
            return AssistantTurnResult(
                content=safety.override_reply,
                safety_level="emergency_escalation",
                clarifying_questions=[],
                metadata={"safety_rule": safety.rule_id, "bypassed_llm": True},
            )

        if safety.safety_level == "boundary_refusal" and safety.override_reply:
            db.add(
                AIInvocationLog(
                    patient_id=patient.id,
                    provider="deterministic_safety",
                    model_name="clinical_safety_v1",
                    prompt_id=prompt.prompt_id,
                    prompt_version=prompt.version,
                    task_type="boundary_refusal",
                    status="succeeded",
                    schema_valid=True,
                    is_synthetic=False,
                )
            )
            return AssistantTurnResult(
                content=safety.override_reply,
                safety_level="boundary_refusal",
                clarifying_questions=safety.clarifying_questions or [],
                metadata={"safety_rule": safety.rule_id, "bypassed_llm": True},
            )

        # 2. Gather grounded patient context + hybrid RAG passages via SEC-012 allowlisted tools
        context_text, citation_index, bundle = await HealthAssistantAgent._gather_patient_context(
            db, patient, user_query=user_message
        )

        # Sliding window of last 8 messages for conversational memory
        recent_history = history_turns[-8:]
        history_text = (
            "\n".join(f"{role.upper()}: {text[:500]}" for role, text in recent_history)
            if recent_history
            else "(Start of conversation)"
        )

        req = GenerationRequest(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.render_user(
                patient_id=str(patient.id),
                patient_context=context_text,
                conversation_history=history_text,
                user_message=user_message,
            ),
            temperature=0.15,
            max_tokens=900,
            expect_json=True,
        )

        active_router = router or _assistant_router()
        provider = active_router.get_provider(cfg.ai_default_provider, is_synthetic_data=False)

        try:
            parsed, gen_resp, attempts = await generate_structured_output(
                provider=provider,
                request=req,
                response_model=AssistantTurnOutput,
                expected_patient_id=patient.id,
                max_retries=cfg.ai_structured_max_retries,
            )

            # Post-LLM safety check (AIR-004 defense-in-depth)
            safe_reply, final_level = enforce_safe_assistant_reply(
                parsed.reply, pre_level="normal"
            )

            # Validate citations strictly against authenticated patient's actual record IDs
            cited: list[dict[str, str]] = [
                citation_index[rid]
                for rid in parsed.cited_record_ids
                if rid in citation_index
            ]
            # Always include verified RAG document page citations retrieved for this query
            seen_labels = {c["label"] for c in cited}
            for h in bundle.get("rag_hits", []):
                cid = h["chunk_id"]
                if cid in citation_index and citation_index[cid]["label"] not in seen_labels:
                    cited.append(citation_index[cid])
                    seen_labels.add(citation_index[cid]["label"])
            if not cited:
                cited = HealthAssistantAgent._match_relevant_citations(
                    user_message, citation_index
                )

            # Format optional proposal-only symptom draft via allowlisted tool (zero DB write!)
            proposed_action: dict[str, Any] | None = None
            if parsed.proposed_symptom is not None:
                proposed_action = await AgentToolRegistry.execute(
                    tool_name="propose_symptom_record",
                    db=db,
                    patient=patient,
                    arguments=parsed.proposed_symptom.model_dump(),
                )

            db.add(
                AIInvocationLog(
                    patient_id=patient.id,
                    provider=gen_resp.provider,
                    model_name=gen_resp.model,
                    prompt_id=prompt.prompt_id,
                    prompt_version=prompt.version,
                    task_type=prompt.task_type,
                    status="succeeded",
                    latency_ms=gen_resp.latency_ms,
                    input_tokens=gen_resp.input_tokens,
                    output_tokens=gen_resp.output_tokens,
                    schema_valid=True,
                    is_synthetic=False,
                )
            )
            return AssistantTurnResult(
                content=safe_reply,
                safety_level=final_level,
                cited_records=cited,
                clarifying_questions=parsed.clarifying_questions,
                proposed_action=proposed_action,
                metadata={
                    "provider": gen_resp.provider,
                    "model": gen_resp.model,
                    "prompt_id": prompt.prompt_id,
                    "prompt_version": prompt.version,
                    "latency_ms": gen_resp.latency_ms,
                    "attempts": attempts,
                },
            )

        except PatientIdentityMismatchError as exc:
            db.add(
                AIInvocationLog(
                    patient_id=patient.id,
                    provider=provider.name,
                    model_name=provider.default_model,
                    prompt_id=prompt.prompt_id,
                    prompt_version=prompt.version,
                    task_type=prompt.task_type,
                    status="schema_invalid",
                    schema_valid=False,
                    is_synthetic=False,
                    error_code=exc.error_code,
                )
            )
            return AssistantTurnResult(
                content=(
                    "I could not verify the safety metadata on my generated response "
                    "(patient identity check). Please try rephrasing your question."
                ),
                safety_level="boundary_refusal",
                metadata={"error_code": exc.error_code},
            )

        except (
            ProviderUnavailableError,
            ProviderTimeoutError,
            StructuredOutputError,
            AIProviderError,
        ) as exc:
            # Graceful record-grounded fallback when local Ollama is offline
            db.add(
                AIInvocationLog(
                    patient_id=patient.id,
                    provider=provider.name,
                    model_name=provider.default_model,
                    prompt_id=prompt.prompt_id,
                    prompt_version=prompt.version,
                    task_type=prompt.task_type,
                    status="provider_unavailable",
                    schema_valid=None,
                    is_synthetic=False,
                    error_code=exc.error_code,
                )
            )
            matched_citations = HealthAssistantAgent._match_relevant_citations(
                user_message, citation_index
            )
            symptom_hint = _detect_symptom_hint(user_message)
            clarifying: list[str] = []
            proposed_action = None
            if symptom_hint is not None:
                sym_name, sym_loc = symptom_hint
                clarifying = [
                    f"When did your {sym_name.lower()} start?",
                    "How severe is it right now (mild, moderate, or severe)?",
                    "Are there any triggers or accompanying symptoms?",
                ]
                proposed_action = await AgentToolRegistry.execute(
                    tool_name="propose_symptom_record",
                    db=db,
                    patient=patient,
                    arguments={
                        "name": sym_name,
                        "severity": "moderate",
                        "body_location": sym_loc,
                        "notes": "Proposed from Health Assistant while local LLM was offline",
                    },
                )

            rec_summary = (
                f"You currently have {len(bundle['conditions'])} condition(s), "
                f"{len(bundle['allergies'])} allergy record(s), "
                f"{len(bundle['symptoms'])} recent symptom(s), and "
                f"{len(bundle['observations'])} confirmed observation(s) in your history."
            )
            reply_text = (
                f"Local AI inference (Ollama) is currently offline, so I am replying in "
                f"record-grounded fallback mode. {rec_summary}"
            )
            if symptom_hint is not None:
                reply_text += (
                    f"\n\nI noticed you mentioned **{symptom_hint[0]}**. I prepared a "
                    "draft symptom entry below that you can review and save to My Health."
                )
            return AssistantTurnResult(
                content=reply_text,
                safety_level="normal",
                cited_records=matched_citations,
                clarifying_questions=clarifying,
                proposed_action=proposed_action,
                metadata={
                    "provider": "offline_fallback",
                    "fallback_reason": exc.error_code,
                },
            )
