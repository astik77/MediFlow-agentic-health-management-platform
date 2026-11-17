"""
API & Integration Tests for Medical Timeline (/api/v1/timeline).
Verifies chronological ordering, occurrence date vs creation date, filtering, search, pagination.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestTimelineAPI:
    async def test_timeline_chronological_ordering_and_filters(
        self, authenticated_client: AsyncClient
    ) -> None:
        # Record historical observation from 2025
        await authenticated_client.post(
            "/api/v1/health-records/observations",
            json={
                "observation_type": "lab_result",
                "display_name": "HbA1c",
                "value_raw": "5.8",
                "unit_raw": "%",
                "observed_at": "2025-06-01T10:00:00Z",
            },
        )

        # Record newer symptom from 2026
        await authenticated_client.post(
            "/api/v1/health-records/symptoms",
            json={
                "name": "Fatigue",
                "severity": "mild",
                "started_at": "2026-11-01T14:00:00Z",
            },
        )

        # Record standalone timeline event from 2026-01-15
        ev_res = await authenticated_client.post(
            "/api/v1/timeline/events",
            json={
                "event_category": "general",
                "title": "Annual Preventive Checkup",
                "summary": "Routine consultation completed",
                "event_occurred_at": "2026-01-15T09:00:00Z",
            },
        )
        assert ev_res.status_code == 201

        # Fetch full timeline — must be sorted descending by event_occurred_at
        tl_res = await authenticated_client.get("/api/v1/timeline")
        assert tl_res.status_code == 200
        tl = tl_res.json()
        assert tl["total"] == 3
        titles = [item["title"] for item in tl["items"]]
        assert titles[0] == "Symptom reported: Fatigue"
        assert titles[1] == "Annual Preventive Checkup"
        assert titles[2].startswith("HbA1c: 5.8 %")

        # Filter by category
        obs_tl = await authenticated_client.get(
            "/api/v1/timeline", params={"category": "observation"}
        )
        assert obs_tl.json()["total"] == 1
        assert obs_tl.json()["items"][0]["event_category"] == "observation"

        # Filter by date range
        range_tl = await authenticated_client.get(
            "/api/v1/timeline",
            params={
                "start_date": "2026-01-01T00:00:00Z",
                "end_date": "2026-06-01T00:00:00Z",
            },
        )
        assert range_tl.json()["total"] == 1
        assert range_tl.json()["items"][0]["title"] == "Annual Preventive Checkup"

        # Search query
        search_tl = await authenticated_client.get(
            "/api/v1/timeline", params={"q": "Preventive"}
        )
        assert search_tl.json()["total"] == 1

        # Pagination
        page_res = await authenticated_client.get(
            "/api/v1/timeline", params={"limit": 2, "offset": 1}
        )
        assert page_res.json()["total"] == 3
        assert len(page_res.json()["items"]) == 2
        assert page_res.json()["items"][0]["title"] == "Annual Preventive Checkup"
