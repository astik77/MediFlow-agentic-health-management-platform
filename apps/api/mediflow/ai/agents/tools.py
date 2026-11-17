"""
SEC-012 Allowlisted Patient-Scoped AI Tool Registry.

SECURITY INVARIANTS:
- Only explicitly registered READ-ONLY or PROPOSAL-ONLY tools can be invoked.
- Zero raw SQL, shell, filesystem, or mutation tools exist.
- Every tool receives `patient: PatientProfile` strictly from the authenticated
  server session — never trusting a model-supplied patient_id.
- Attempting to call an unregistered tool raises `UnauthorizedToolError` (SEC-012).
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.logging import get_logger
from mediflow.modules.documents.models import Document
from mediflow.modules.health_records.models import (
    HealthObservation,
    PatientAllergy,
    PatientCondition,
    PatientSymptom,
)
from mediflow.modules.patients.models import PatientProfile

logger = get_logger(__name__)


class UnauthorizedToolError(Exception):
    """SEC-012: Raised when an agent or caller attempts to invoke a disallowed tool."""

    error_code = "sec012_unauthorized_tool"


ToolHandler = Callable[[AsyncSession, PatientProfile, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Metadata and handler for an allowlisted patient-scoped agent tool."""

    name: str
    mode: str  # read_only | proposal_only
    description: str
    handler: ToolHandler


async def _tool_profile_summary(
    _db: AsyncSession, patient: PatientProfile, _args: dict[str, Any]
) -> dict[str, Any]:
    return {
        "patient_id": str(patient.id),
        "biological_sex": patient.biological_sex,
        "blood_group": patient.blood_group,
        "height_cm": patient.height_cm,
        "weight_kg": patient.weight_kg,
        "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
    }


async def _tool_active_conditions(
    db: AsyncSession, patient: PatientProfile, args: dict[str, Any]
) -> dict[str, Any]:
    limit = min(max(int(args.get("limit", 10)), 1), 25)
    rows = (
        await db.execute(
            select(PatientCondition)
            .where(
                PatientCondition.patient_id == patient.id,
                PatientCondition.is_archived.is_(False),
            )
            .order_by(PatientCondition.updated_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "conditions": [
            {
                "id": str(c.id),
                "name": c.name,
                "status": c.status,
                "severity": c.severity,
                "onset_date": c.onset_date.isoformat() if c.onset_date else None,
            }
            for c in rows
        ]
    }


async def _tool_allergies(
    db: AsyncSession, patient: PatientProfile, args: dict[str, Any]
) -> dict[str, Any]:
    limit = min(max(int(args.get("limit", 10)), 1), 25)
    rows = (
        await db.execute(
            select(PatientAllergy)
            .where(
                PatientAllergy.patient_id == patient.id,
                PatientAllergy.is_archived.is_(False),
            )
            .order_by(PatientAllergy.updated_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "allergies": [
            {
                "id": str(a.id),
                "allergen": a.allergen,
                "category": a.category,
                "severity": a.severity,
                "reaction": a.reaction,
                "status": a.status,
            }
            for a in rows
        ]
    }


async def _tool_recent_symptoms(
    db: AsyncSession, patient: PatientProfile, args: dict[str, Any]
) -> dict[str, Any]:
    limit = min(max(int(args.get("limit", 10)), 1), 25)
    rows = (
        await db.execute(
            select(PatientSymptom)
            .where(
                PatientSymptom.patient_id == patient.id,
                PatientSymptom.is_archived.is_(False),
            )
            .order_by(PatientSymptom.started_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "symptoms": [
            {
                "id": str(s.id),
                "name": s.name,
                "severity": s.severity,
                "status": s.status,
                "body_location": s.body_location,
                "started_at": s.started_at.isoformat(),
            }
            for s in rows
        ]
    }


async def _tool_recent_observations(
    db: AsyncSession, patient: PatientProfile, args: dict[str, Any]
) -> dict[str, Any]:
    limit = min(max(int(args.get("limit", 15)), 1), 30)
    rows = (
        await db.execute(
            select(HealthObservation)
            .where(
                HealthObservation.patient_id == patient.id,
                HealthObservation.is_archived.is_(False),
                HealthObservation.review_status == "confirmed",
            )
            .order_by(HealthObservation.observed_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "observations": [
            {
                "id": str(o.id),
                "display_name": o.display_name,
                "value_raw": o.value_raw,
                "unit_raw": o.unit_raw,
                "reference_range_text": o.reference_range_text,
                "abnormality_flag": o.abnormality_flag,
                "observed_at": o.observed_at.isoformat(),
            }
            for o in rows
        ]
    }


async def _tool_recent_documents(
    db: AsyncSession, patient: PatientProfile, args: dict[str, Any]
) -> dict[str, Any]:
    limit = min(max(int(args.get("limit", 8)), 1), 20)
    rows = (
        await db.execute(
            select(Document)
            .where(
                Document.patient_id == patient.id,
                Document.is_archived.is_(False),
            )
            .order_by(Document.uploaded_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {
        "documents": [
            {
                "id": str(d.id),
                "title": d.title,
                "document_type": d.document_type,
                "document_date": d.document_date.isoformat() if d.document_date else None,
                "review_status": d.review_status,
            }
            for d in rows
        ]
    }


async def _tool_propose_symptom_record(
    _db: AsyncSession, patient: PatientProfile, args: dict[str, Any]
) -> dict[str, Any]:
    """Proposal-only tool: formats a symptom draft without mutating the database."""
    name = str(args.get("name", "")).strip()[:255]
    severity = str(args.get("severity", "moderate")).strip().lower()
    if severity not in {"mild", "moderate", "severe"}:
        severity = "moderate"
    return {
        "proposal_type": "symptom",
        "status": "pending",
        "patient_id": str(patient.id),
        "payload": {
            "name": name,
            "severity": severity,
            "body_location": (
                str(args["body_location"]).strip()[:150] if args.get("body_location") else None
            ),
            "frequency": (
                str(args["frequency"]).strip()[:100] if args.get("frequency") else None
            ),
            "notes": str(args["notes"]).strip()[:500] if args.get("notes") else None,
        },
    }


class AgentToolRegistry:
    """Strict allowlist registry enforcing SEC-012 tool execution boundaries."""

    _TOOLS: ClassVar[dict[str, ToolDefinition]] = {
        "get_patient_profile_summary": ToolDefinition(
            name="get_patient_profile_summary",
            mode="read_only",
            description="Read authenticated patient's baseline demographics.",
            handler=_tool_profile_summary,
        ),
        "list_active_conditions": ToolDefinition(
            name="list_active_conditions",
            mode="read_only",
            description="List authenticated patient's non-archived conditions.",
            handler=_tool_active_conditions,
        ),
        "list_allergies": ToolDefinition(
            name="list_allergies",
            mode="read_only",
            description="List authenticated patient's non-archived allergies.",
            handler=_tool_allergies,
        ),
        "list_recent_symptoms": ToolDefinition(
            name="list_recent_symptoms",
            mode="read_only",
            description="List authenticated patient's recent symptoms.",
            handler=_tool_recent_symptoms,
        ),
        "list_recent_observations": ToolDefinition(
            name="list_recent_observations",
            mode="read_only",
            description="List authenticated patient's confirmed lab & vital observations.",
            handler=_tool_recent_observations,
        ),
        "list_recent_documents": ToolDefinition(
            name="list_recent_documents",
            mode="read_only",
            description="List authenticated patient's active uploaded documents.",
            handler=_tool_recent_documents,
        ),
        "propose_symptom_record": ToolDefinition(
            name="propose_symptom_record",
            mode="proposal_only",
            description="Create an unsaved symptom draft requiring explicit patient approval.",
            handler=_tool_propose_symptom_record,
        ),
    }

    @classmethod
    def allowed_tool_names(cls) -> list[str]:
        return sorted(cls._TOOLS.keys())

    @classmethod
    async def execute(
        cls,
        *,
        tool_name: str,
        db: AsyncSession,
        patient: PatientProfile,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute an allowlisted patient-scoped tool.
        Raises UnauthorizedToolError (SEC-012) for any unregistered tool name.
        """
        tool = cls._TOOLS.get(tool_name)
        if tool is None:
            logger.warning(
                "sec012_unauthorized_tool_blocked",
                tool_name=tool_name,
                patient_id=str(patient.id),
            )
            raise UnauthorizedToolError(
                f"Tool '{tool_name}' is not authorized in MEDIFLOW's allowlisted "
                "patient-scoped tool registry (SEC-012)."
            )
        return await tool.handler(db, patient, arguments or {})
