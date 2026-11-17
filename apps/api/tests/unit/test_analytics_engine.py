"""
Unit tests for Phase 8 Deterministic Biomarker Trend Engine.
Verifies reference-range parsing, trend direction math, unit-safety guard,
time-window filtering, and Candidate Governance Invariant.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from mediflow.modules.analytics.trends import (
    build_biomarker_trend_series,
    compute_trend_direction,
    parse_reference_range_bounds,
)
from mediflow.modules.health_records.models import HealthObservation


def _make_obs(
    *,
    display_name: str = "HbA1c",
    value_raw: str = "6.2",
    unit_raw: str | None = "%",
    value_numeric: float | None = 6.2,
    value_normalized: float | None = None,
    unit_normalized: str | None = None,
    reference_range_text: str | None = "4.0 - 5.6 %",
    abnormality_flag: str | None = "high",
    review_status: str = "confirmed",
    is_archived: bool = False,
    observed_at: datetime | None = None,
) -> HealthObservation:
    now = observed_at or datetime.now(UTC)
    return HealthObservation(
        id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        observation_type="lab_result",
        display_name=display_name,
        value_raw=value_raw,
        unit_raw=unit_raw,
        value_numeric=value_numeric,
        value_normalized=value_normalized,
        unit_normalized=unit_normalized,
        reference_range_text=reference_range_text,
        abnormality_flag=abnormality_flag,
        observed_at=now,
        review_status=review_status,
        is_archived=is_archived,
        created_at=now,
        updated_at=now,
    )


def test_parse_reference_range_bounds() -> None:
    assert parse_reference_range_bounds("12.0 - 16.0 g/dL") == (12.0, 16.0)
    assert parse_reference_range_bounds("70 to 99 mg/dL") == (70.0, 99.0)
    assert parse_reference_range_bounds("4.0 \u2013 5.6 %") == (4.0, 5.6)
    assert parse_reference_range_bounds("< 200 mg/dL") == (None, 200.0)
    assert parse_reference_range_bounds("<= 5.7%") == (None, 5.7)
    assert parse_reference_range_bounds("> 40 mg/dL") == (40.0, None)
    assert parse_reference_range_bounds(">= 60 mL/min") == (60.0, None)
    assert parse_reference_range_bounds("Negative") == (None, None)
    assert parse_reference_range_bounds(None) == (None, None)


def test_compute_trend_direction() -> None:
    assert compute_trend_direction(None, 6.5) == (None, None, "insufficient_data")
    assert compute_trend_direction(100.0, 101.0) == (1.0, 1.0, "stable")
    assert compute_trend_direction(100.0, 110.0) == (10.0, 10.0, "increasing")
    assert compute_trend_direction(100.0, 92.0) == (-8.0, -8.0, "decreasing")
    assert compute_trend_direction(0.0, 0.0) == (0.0, None, "stable")
    assert compute_trend_direction(0.0, 3.0) == (3.0, None, "increasing")


def test_build_trends_excludes_candidates_archived_and_non_numeric() -> None:
    now = datetime.now(UTC)
    observations = [
        _make_obs(value_raw="6.0", value_numeric=6.0, observed_at=now - timedelta(days=20)),
        _make_obs(value_raw="6.4", value_numeric=6.4, observed_at=now - timedelta(days=5)),
        # Must be excluded: candidate
        _make_obs(
            value_raw="9.9",
            value_numeric=9.9,
            review_status="candidate",
            observed_at=now - timedelta(days=1),
        ),
        # Must be excluded: rejected
        _make_obs(
            value_raw="11.0",
            value_numeric=11.0,
            review_status="rejected",
            observed_at=now,
        ),
        # Must be excluded: archived
        _make_obs(
            value_raw="8.8",
            value_numeric=8.8,
            is_archived=True,
            observed_at=now,
        ),
        # Must be excluded: non-numeric
        _make_obs(
            display_name="Blood Pressure",
            value_raw="120/80",
            unit_raw="mmHg",
            value_numeric=None,
            observed_at=now,
        ),
    ]

    series = build_biomarker_trend_series(observations, now=now)
    assert len(series) == 1
    hba1c = series[0]
    assert hba1c.display_name == "HbA1c"
    assert hba1c.point_count == 2
    assert [p.value for p in hba1c.points] == [6.0, 6.4]
    assert hba1c.direction == "increasing"
    assert hba1c.reference_low == 4.0
    assert hba1c.reference_high == 5.6


def test_build_trends_uses_normalized_values_and_blocks_incompatible_units() -> None:
    now = datetime.now(UTC)
    observations = [
        # Older glucose in mmol/L normalized to mg/dL -> compatible!
        _make_obs(
            display_name="Fasting Blood Glucose",
            value_raw="5.5",
            unit_raw="mmol/L",
            value_numeric=5.5,
            value_normalized=99.1,
            unit_normalized="mg/dL",
            reference_range_text="70 - 99 mg/dL",
            observed_at=now - timedelta(days=40),
        ),
        # Stray incompatible unit with no normalization -> must NOT mix onto mg/dL Y-axis!
        _make_obs(
            display_name="Fasting Blood Glucose",
            value_raw="50",
            unit_raw="U/L",
            value_numeric=50.0,
            value_normalized=None,
            unit_normalized=None,
            observed_at=now - timedelta(days=20),
        ),
        # Latest glucose in mg/dL
        _make_obs(
            display_name="Fasting Blood Glucose",
            value_raw="110",
            unit_raw="mg/dL",
            value_numeric=110.0,
            value_normalized=110.0,
            unit_normalized="mg/dL",
            reference_range_text="70 - 99 mg/dL",
            observed_at=now - timedelta(days=2),
        ),
    ]

    series = build_biomarker_trend_series(observations, now=now)
    assert len(series) == 1
    glucose = series[0]
    assert glucose.unit == "mg/dL"
    assert glucose.point_count == 2
    assert [p.value for p in glucose.points] == [99.1, 110.0]
    assert glucose.direction == "increasing"


def test_build_trends_window_and_biomarker_filter() -> None:
    now = datetime.now(UTC)
    observations = [
        _make_obs(
            display_name="Hemoglobin",
            value_raw="13.5",
            unit_raw="g/dL",
            value_numeric=13.5,
            observed_at=now - timedelta(days=120),
        ),
        _make_obs(
            display_name="Hemoglobin",
            value_raw="14.1",
            unit_raw="g/dL",
            value_numeric=14.1,
            observed_at=now - timedelta(days=10),
        ),
        _make_obs(
            display_name="TSH",
            value_raw="2.4",
            unit_raw="mIU/L",
            value_numeric=2.4,
            observed_at=now - timedelta(days=5),
        ),
    ]

    s_30d = build_biomarker_trend_series(observations, window="30d", now=now)
    by_key_30d = {s.biomarker_key: s for s in s_30d}
    assert by_key_30d["hemoglobin"].point_count == 1
    assert by_key_30d["hemoglobin"].direction == "insufficient_data"

    s_filtered = build_biomarker_trend_series(
        observations, window="all", biomarker_filter="  hemoglobin ", now=now
    )
    assert len(s_filtered) == 1
    assert s_filtered[0].biomarker_key == "hemoglobin"
    assert s_filtered[0].point_count == 2
