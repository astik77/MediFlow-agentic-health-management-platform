"""
Phase 6 Unit Tests — Clinical Safety Triage (AIR-004) & SEC-012 Allowlisted AI Tools.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.ai.agents.tools import AgentToolRegistry, UnauthorizedToolError
from mediflow.ai.safety.clinical_safety import (
    enforce_safe_assistant_reply,
    evaluate_user_message_safety,
)
from mediflow.modules.auth.models import User
from mediflow.modules.patients.models import PatientProfile


class TestClinicalSafetyLayer:
    def test_emergency_red_flags_escalate_immediately(self) -> None:
        emergencies = [
            "I have crushing chest pain radiating to my left arm",
            "Sudden facial droop and slurred speech",
            "My throat is swelling and I cannot breathe",
            "I am vomiting blood right now",
            "I want to kill myself tonight",
        ]
        for text in emergencies:
            res = evaluate_user_message_safety(text)
            assert res.safety_level == "emergency_escalation", f"Failed to escalate: {text}"
            assert res.override_reply is not None
            assert "112" in res.override_reply

    def test_negated_red_flags_do_not_false_escalate(self) -> None:
        res = evaluate_user_message_safety(
            "I have mild fatigue today with no chest pain and no shortness of breath."
        )
        assert res.safety_level == "normal"

    def test_diagnosis_prescribing_and_dosage_requests_refused(self) -> None:
        boundary_prompts = [
            "Should I double my metformin dose today?",
            "Can I stop taking my blood pressure medication?",
            "Please prescribe me an antibiotic for my cough.",
            "Diagnose me based on my hemoglobin result.",
        ]
        for text in boundary_prompts:
            res = evaluate_user_message_safety(text)
            assert res.safety_level == "boundary_refusal", f"Failed boundary check: {text}"
            assert res.override_reply is not None

    def test_post_llm_filter_intercepts_unsafe_directives(self) -> None:
        reply, level = enforce_safe_assistant_reply(
            "You should stop taking your blood pressure medication tomorrow.",
            pre_level="normal",
        )
        assert level == "boundary_refusal"
        assert "cannot recommend" in reply.lower()

        safe_text = "Your last recorded hemoglobin was 13.5 g/dL, which is within reference range."
        reply2, level2 = enforce_safe_assistant_reply(safe_text, pre_level="normal")
        assert level2 == "normal"
        assert reply2 == safe_text


class TestSec012AllowlistedTools:
    @pytest.mark.asyncio
    async def test_sec012_blocks_unauthorized_tools(
        self,
        db_session: AsyncSession,
        test_patient: tuple[User, PatientProfile, str],
    ) -> None:
        _, profile, _ = test_patient
        for forbidden in ("execute_sql", "drop_table", "run_shell", "read_file", "delete_all"):
            with pytest.raises(UnauthorizedToolError):
                await AgentToolRegistry.execute(
                    tool_name=forbidden,
                    db=db_session,
                    patient=profile,
                    arguments={"query": "SELECT * FROM users"},
                )

    @pytest.mark.asyncio
    async def test_allowlisted_read_only_and_proposal_tools_work(
        self,
        db_session: AsyncSession,
        test_patient: tuple[User, PatientProfile, str],
    ) -> None:
        _, profile, _ = test_patient
        prof = await AgentToolRegistry.execute(
            tool_name="get_patient_profile_summary",
            db=db_session,
            patient=profile,
        )
        assert prof["patient_id"] == str(profile.id)

        prop = await AgentToolRegistry.execute(
            tool_name="propose_symptom_record",
            db=db_session,
            patient=profile,
            arguments={"name": "Headache", "severity": "mild", "body_location": "head"},
        )
        assert prop["proposal_type"] == "symptom"
        assert prop["status"] == "pending"
        assert prop["payload"]["name"] == "Headache"
