"""
Deterministic Biomarker Trend Engine (Phase 8).

Pure, zero-I/O longitudinal time-series calculations:
- Strictly enforces the Candidate Governance Invariant (confirmed, non-archived only).
- Unit-safe grouping: uses value_normalized / unit_normalized when available,
  falling back to value_numeric / unit_raw, and refuses to mix incompatible units
  on a single Y-axis.
- Parses numeric reference-range bounds for normal-band chart shading.
"""
from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from mediflow.modules.analytics.schemas import (
    BiomarkerTrendSeries,
    TrendDataPoint,
    TrendDirection,
    TrendWindow,
)
from mediflow.modules.health_records.models import HealthObservation

_RANGE_BETWEEN_RE = re.compile(
    r"(?P<low>-?\d+(?:\.\d+)?)\s*(?:-|\u2013|\u2014|to)\s*(?P<high>-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_RANGE_UPPER_RE = re.compile(
    r"(?:<=|<|≤|up\s+to|below|under)\s*(?P<high>-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_RANGE_LOWER_RE = re.compile(
    r"(?:>=|>|≥|above|over|at\s+least)\s*(?P<low>-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def ensure_utc(dt: datetime) -> datetime:
    """Normalize timezone-naive datetimes (e.g., from SQLite) to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def normalize_biomarker_key(display_name: str) -> str:
    """Canonical lowercase key for grouping biomarker observations."""
    return " ".join(display_name.strip().lower().split())


def normalize_unit_key(unit: str | None) -> str:
    """Canonical lowercase key for comparing measurement units safely."""
    if not unit:
        return ""
    return "".join(unit.strip().lower().split())


def parse_reference_range_bounds(
    range_text: str | None,
) -> tuple[float | None, float | None]:
    """
    Parse a human-readable reference range string into numeric (low, high) bounds
    for Recharts ReferenceArea shading.
    Examples:
    - "12.0 - 16.0 g/dL" -> (12.0, 16.0)
    - "70 to 99 mg/dL"   -> (70.0, 99.0)
    - "< 200 mg/dL"      -> (None, 200.0)
    - "> 40 mg/dL"       -> (40.0, None)
    - "Negative"         -> (None, None)
    """
    if not range_text or not range_text.strip():
        return None, None

    cleaned = range_text.strip()
    m_between = _RANGE_BETWEEN_RE.search(cleaned)
    if m_between:
        low = float(m_between.group("low"))
        high = float(m_between.group("high"))
        return (low, high) if low <= high else (high, low)

    m_upper = _RANGE_UPPER_RE.search(cleaned)
    if m_upper:
        return None, float(m_upper.group("high"))

    m_lower = _RANGE_LOWER_RE.search(cleaned)
    if m_lower:
        return float(m_lower.group("low")), None

    return None, None


def resolve_numeric_value_and_unit(
    obs: HealthObservation,
) -> tuple[float | None, str | None]:
    """
    Prefer normalized numeric value + unit when available (so convertible units
    like mmol/L and mg/dL plot cleanly on one canonical scale); fall back to
    raw numeric value + raw unit. Returns (None, None) for non-numeric results.
    """
    if obs.value_normalized is not None:
        return float(obs.value_normalized), (obs.unit_normalized or obs.unit_raw)
    if obs.value_numeric is not None:
        return float(obs.value_numeric), obs.unit_raw
    return None, None


def compute_trend_direction(
    previous: float | None,
    latest: float,
    *,
    stable_threshold_pct: float = 2.0,
) -> tuple[float | None, float | None, TrendDirection]:
    """
    Compute absolute delta, percentage delta, and clinical trend direction
    between the second-to-last and latest measurements.
    Changes within +/- stable_threshold_pct (default 2.0%) are classified as 'stable'.
    """
    if previous is None:
        return None, None, "insufficient_data"

    delta_abs = round(latest - previous, 4)
    if abs(previous) > 1e-9:
        delta_pct: float | None = round(((latest - previous) / abs(previous)) * 100.0, 2)
        if abs(delta_pct) < stable_threshold_pct:
            return delta_abs, delta_pct, "stable"
        return delta_abs, delta_pct, ("increasing" if delta_pct > 0 else "decreasing")

    if abs(delta_abs) < 1e-9:
        return 0.0, None, "stable"
    return delta_abs, None, ("increasing" if delta_abs > 0 else "decreasing")


def window_cutoff(window: TrendWindow, *, now: datetime | None = None) -> datetime | None:
    """Return the UTC start boundary for a trend window ('30d', '90d', '1y', 'all')."""
    ref = ensure_utc(now) if now is not None else datetime.now(UTC)
    if window == "30d":
        return ref - timedelta(days=30)
    if window == "90d":
        return ref - timedelta(days=90)
    if window == "1y":
        return ref - timedelta(days=365)
    return None


def build_biomarker_trend_series(
    observations: Sequence[HealthObservation],
    *,
    window: TrendWindow = "all",
    biomarker_filter: str | None = None,
    now: datetime | None = None,
) -> list[BiomarkerTrendSeries]:
    """
    Group confirmed numeric observations into unit-safe longitudinal BiomarkerTrendSeries.

    Invariants:
    - Excludes any observation with review_status != 'confirmed' or is_archived == True.
    - Excludes non-numeric observations (e.g., 'Positive', '120/80').
    - Refuses to plot observations with incompatible units on the same series
      (anchors to the unit of the most recent observation for that biomarker).
    """
    cutoff = window_cutoff(window, now=now)
    normalized_filter = (
        normalize_biomarker_key(biomarker_filter)
        if biomarker_filter and biomarker_filter.strip()
        else None
    )

    grouped: dict[str, list[tuple[HealthObservation, float, str | None]]] = defaultdict(list)

    for obs in observations:
        if obs.review_status != "confirmed" or obs.is_archived:
            continue

        obs_time = ensure_utc(obs.observed_at)
        if cutoff is not None and obs_time < cutoff:
            continue

        val, unit = resolve_numeric_value_and_unit(obs)
        if val is None:
            continue

        bkey = normalize_biomarker_key(obs.display_name)
        if not bkey:
            continue
        if normalized_filter is not None and bkey != normalized_filter:
            continue

        grouped[bkey].append((obs, val, unit))

    series_list: list[BiomarkerTrendSeries] = []
    for bkey, entries in grouped.items():
        # Sort chronologically ascending (tie-break by created_at)
        entries.sort(key=lambda e: (ensure_utc(e[0].observed_at), ensure_utc(e[0].created_at)))

        latest_obs, _, latest_unit = entries[-1]
        anchor_unit_key = normalize_unit_key(latest_unit)

        # Unit-safety guard: keep only observations matching the canonical latest unit
        unit_safe_entries = [
            e for e in entries if normalize_unit_key(e[2]) == anchor_unit_key
        ]
        if not unit_safe_entries:
            continue

        points = [
            TrendDataPoint(
                observation_id=obs.id,
                observed_at=ensure_utc(obs.observed_at),
                value=round(val, 4),
                unit=unit,
                value_raw=obs.value_raw,
                unit_raw=obs.unit_raw,
                reference_range_text=obs.reference_range_text,
                abnormality_flag=obs.abnormality_flag,
                source_document_id=obs.source_document_id,
            )
            for obs, val, unit in unit_safe_entries
        ]

        values = [p.value for p in points]
        latest_pt = points[-1]
        prev_val = points[-2].value if len(points) >= 2 else None
        delta_abs, delta_pct, direction = compute_trend_direction(prev_val, latest_pt.value)

        # Find most recent non-empty reference range text across the series
        ref_text = next(
            (p.reference_range_text for p in reversed(points) if p.reference_range_text),
            None,
        )
        ref_low, ref_high = parse_reference_range_bounds(ref_text)

        series_list.append(
            BiomarkerTrendSeries(
                biomarker_key=bkey,
                display_name=latest_obs.display_name.strip(),
                unit=latest_unit,
                observation_type=latest_obs.observation_type,
                point_count=len(points),
                latest_value=latest_pt.value,
                latest_observed_at=latest_pt.observed_at,
                latest_abnormality_flag=latest_pt.abnormality_flag,
                previous_value=prev_val,
                delta_absolute=delta_abs,
                delta_percent=delta_pct,
                direction=direction,
                min_value=round(min(values), 4),
                max_value=round(max(values), 4),
                mean_value=round(sum(values) / len(values), 4),
                reference_low=ref_low,
                reference_high=ref_high,
                reference_range_text=ref_text,
                points=points,
            )
        )

    # Most recently observed biomarker first, then alphabetical
    series_list.sort(key=lambda s: (-s.latest_observed_at.timestamp(), s.display_name.lower()))
    return series_list
