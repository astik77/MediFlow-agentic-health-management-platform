"""
Medical Timeline API Endpoints (v1)
Provides chronological retrieval, filtering, search, and patient-reported event logging.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from mediflow.core.database import get_db
from mediflow.core.dependencies import get_current_patient
from mediflow.modules.health_records.schemas import (
    HealthEventCreate,
    HealthEventResponse,
    TimelineResponse,
)
from mediflow.modules.health_records.service import HealthRecordsService
from mediflow.modules.patients.models import PatientProfile

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("", response_model=TimelineResponse)
async def get_medical_timeline(
    category: str | None = Query(None, description="Filter by event_category"),
    start_date: datetime | None = Query(None, description="Filter events on/after ISO timestamp"),
    end_date: datetime | None = Query(None, description="Filter events on/before ISO timestamp"),
    q: str | None = Query(None, description="Search event title or summary"),
    review_status: str | None = Query(None, description="Filter by review_status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return paginated chronological medical timeline scoped to the authenticated patient."""
    items, total = await HealthRecordsService.list_timeline(
        db,
        current_patient,
        category=category,
        start_date=start_date,
        end_date=end_date,
        search=q,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )
    return TimelineResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/events",
    response_model=HealthEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_timeline_event(
    payload: HealthEventCreate,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Record a standalone patient-reported health update on the medical timeline."""
    return await HealthRecordsService.create_timeline_event(db, current_patient, payload)


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an event from the patient's medical timeline",
)
async def delete_timeline_event(
    event_id: str,
    current_patient: PatientProfile = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
) -> None:
    import uuid
    try:
        parsed_id = uuid.UUID(event_id)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid event UUID.")
    await HealthRecordsService.delete_timeline_event(db, current_patient, parsed_id)
