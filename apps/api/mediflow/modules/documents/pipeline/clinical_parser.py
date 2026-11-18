"""
Clinical Fact, Lab Observation, Date & Unit Parser.
Deterministically extracts candidate HealthObservation records from extracted document
text while strictly preserving raw values, raw units, reference ranges, normalized values,
and provenance metadata. Never produces confirmed records directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Clinical Date Extraction (India & International Formats)
# ---------------------------------------------------------------------------

_MONTH_MAP: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

# Context keywords prioritizing report/collection/discharge/visit dates over DOB & admission
_PRIORITY_DATE_LABELS_TIER1 = re.compile(
    r"(?:date\s*of\s*discharge|discharge\s*date|report\s*date|sample\s*collected|"
    r"collection\s*date|test\s*date|date\s*of\s*report|visit\s*date|exam\s*date|"
    r"reported\s*on|collected\s*on)\s*[:\-]?\s*([^\n]{6,32})",
    re.IGNORECASE,
)

_PRIORITY_DATE_LABELS_TIER2 = re.compile(
    r"(?:^|\b)(?:dated|date)\s*[:\-]\s*([^\n]{6,32})",
    re.IGNORECASE,
)

_DOB_CONTEXT = re.compile(r"\b(dob|date\s+of\s+birth|birth\s+date)\b", re.IGNORECASE)

_ISO_DATE_RE = re.compile(r"\b(20\d{2}|19\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b")
_DMY_TEXT_RE = re.compile(
    r"\b(\d{1,2})[\s\-/]+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)[,\s\-/]+(20\d{2}|19\d{2})\b",
    re.IGNORECASE,
)
_MDY_TEXT_RE = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?[,\s]+(20\d{2}|19\d{2})\b",
    re.IGNORECASE,
)
_NUMERIC_SLASH_RE = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](20\d{2}|19\d{2})\b")


def parse_single_date(text: str, *, prefer_dmy: bool = True) -> date | None:
    """Parse the first valid calendar date from a short string snippet."""
    m = _ISO_DATE_RE.search(text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d)
        except ValueError:
            pass

    m = _DMY_TEXT_RE.search(text)
    if m:
        d, mo_str, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        mo = _MONTH_MAP.get(mo_str[:3], 0)
        try:
            return date(y, mo, d)
        except ValueError:
            pass

    m = _MDY_TEXT_RE.search(text)
    if m:
        mo_str, d, y = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        mo = _MONTH_MAP.get(mo_str[:3], 0)
        try:
            return date(y, mo, d)
        except ValueError:
            pass

    m = _NUMERIC_SLASH_RE.search(text)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Disambiguate when one part > 12; otherwise respect India/international DMY default
        if a > 12 and b <= 12:
            d, mo = a, b
        elif b > 12 and a <= 12:
            mo, d = a, b
        elif prefer_dmy:
            d, mo = a, b
        else:
            mo, d = a, b
        try:
            return date(y, mo, d)
        except ValueError:
            pass

    return None


def extract_clinical_date(text: str, *, prefer_dmy: bool = True) -> date | None:
    """
    Extract the primary clinical date (report/collection/discharge/visit date) from a document.
    Prioritizes explicitly labeled clinical dates (Tier 1) before generic 'Date:' labels (Tier 2),
    and skips DOB lines.
    """
    for pattern in (_PRIORITY_DATE_LABELS_TIER1, _PRIORITY_DATE_LABELS_TIER2):
        for m in pattern.finditer(text):
            snippet = m.group(1)
            parsed = parse_single_date(snippet, prefer_dmy=prefer_dmy)
            if parsed is not None:
                return parsed

    for line in text.splitlines():
        if _DOB_CONTEXT.search(line):
            continue
        parsed = parse_single_date(line, prefer_dmy=prefer_dmy)
        if parsed is not None:
            return parsed
    return None


# ---------------------------------------------------------------------------
# Unit Normalization (Preserving Raw Values & Units)
# ---------------------------------------------------------------------------

_UNIT_CANONICAL: dict[str, str] = {
    "g/dl": "g/dL",
    "gm/dl": "g/dL",
    "g/l": "g/L",
    "mg/dl": "mg/dL",
    "mg%": "mg/dL",
    "mmol/l": "mmol/L",
    "umol/l": "umol/L",
    "µmol/l": "umol/L",
    "miu/l": "mIU/L",
    "uiu/ml": "uIU/mL",
    "µiu/ml": "uIU/mL",
    "u/l": "U/L",
    "iu/l": "IU/L",
    "meq/l": "mEq/L",
    "ng/ml": "ng/mL",
    "pg/ml": "pg/mL",
    "10^3/ul": "10^3/uL",
    "10^3/µl": "10^3/uL",
    "x10^3/ul": "10^3/uL",
    "k/ul": "10^3/uL",
    "thou/ul": "10^3/uL",
    "10^6/ul": "10^6/uL",
    "10^6/µl": "10^6/uL",
    "mill/cumm": "10^6/uL",
    "cells/cumm": "cells/uL",
    "cells/mcl": "cells/uL",
    "/cumm": "cells/uL",
    "lakhs/cumm": "lakhs/cumm",
    "fl": "fL",
    "pg": "pg",
    "%": "%",
    "mmhg": "mmHg",
    "bpm": "bpm",
    "/min": "/min",
    "kg": "kg",
    "lbs": "lbs",
    "lb": "lbs",
    "cm": "cm",
    "°c": "C",
    "c": "C",
    "°f": "F",
    "f": "F",
    "mm/hr": "mm/hr",
    "mg/l": "mg/L",
    "/hpf": "/hpf",
    "sec": "sec",
}


def normalize_unit_and_value(
    test_name: str, value_numeric: float | None, unit_raw: str | None
) -> tuple[float | None, str | None]:
    """
    Normalize common clinical units to canonical SI/conventional equivalents
    while NEVER mutating value_raw or unit_raw.
    """
    if unit_raw is None:
        return value_numeric, None

    key = unit_raw.strip().lower().replace(" ", "")
    canon = _UNIT_CANONICAL.get(key, unit_raw.strip())
    if value_numeric is None:
        return None, canon

    name_l = test_name.lower()

    # Glucose: mmol/L -> mg/dL (factor 18.0182)
    if "glucose" in name_l and canon == "mmol/L":
        return round(value_numeric * 18.0182, 2), "mg/dL"

    # Cholesterol / LDL / HDL: mmol/L -> mg/dL (factor 38.67)
    if any(k in name_l for k in ("cholesterol", "ldl", "hdl")) and canon == "mmol/L":
        return round(value_numeric * 38.67, 2), "mg/dL"

    # Triglycerides: mmol/L -> mg/dL (factor 88.57)
    if "triglyceride" in name_l and canon == "mmol/L":
        return round(value_numeric * 88.57, 2), "mg/dL"

    # Creatinine: umol/L -> mg/dL (divide by 88.4)
    if "creatinine" in name_l and canon == "umol/L":
        return round(value_numeric / 88.4, 2), "mg/dL"

    # Hemoglobin: g/L -> g/dL (divide by 10)
    if ("hemoglobin" in name_l or "haemoglobin" in name_l) and canon == "g/L":
        return round(value_numeric / 10.0, 2), "g/dL"

    # Weight: lbs -> kg
    if canon == "lbs":
        return round(value_numeric * 0.453592, 2), "kg"

    # Temperature: F -> C
    if ("temp" in name_l or "temperature" in name_l) and canon == "F":
        return round((value_numeric - 32.0) * 5.0 / 9.0, 2), "C"

    return value_numeric, canon


# ---------------------------------------------------------------------------
# Reference Range & Abnormality Evaluation
# ---------------------------------------------------------------------------

_RANGE_BOUNDS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|\u2013|to)\s*(\d+(?:\.\d+)?)", re.I)
_RANGE_LT_RE = re.compile(r"<\s*=?\s*(\d+(?:\.\d+)?)")
_RANGE_GT_RE = re.compile(r">\s*=?\s*(\d+(?:\.\d+)?)")

# Standard clinical reference ranges for common biomarkers when missing from document OCR
DEFAULT_BIOMARKER_RANGES: dict[str, tuple[float, float, str]] = {
    "hemoglobin": (12.0, 17.5, "g/dL"),
    "fasting blood sugar": (70.0, 100.0, "mg/dL"),
    "blood sugar": (70.0, 100.0, "mg/dL"),
    "glucose": (70.0, 100.0, "mg/dL"),
    "random blood sugar": (70.0, 140.0, "mg/dL"),
    "postprandial blood sugar": (70.0, 140.0, "mg/dL"),
    "hba1c": (4.0, 5.7, "%"),
    "platelets": (150000.0, 450000.0, "/uL"),
    "platelet count": (150000.0, 450000.0, "/uL"),
    "wbc": (4000.0, 11000.0, "/uL"),
    "total leucocyte count": (4000.0, 11000.0, "/uL"),
    "white blood cells": (4000.0, 11000.0, "/uL"),
    "rbc": (4.0, 6.0, "mill/cumm"),
    "red blood cell count": (4.0, 6.0, "mill/cumm"),
    "creatinine": (0.6, 1.2, "mg/dL"),
    "serum creatinine": (0.6, 1.2, "mg/dL"),
    "blood urea": (15.0, 40.0, "mg/dL"),
    "urea": (15.0, 40.0, "mg/dL"),
    "bun": (7.0, 20.0, "mg/dL"),
    "total cholesterol": (100.0, 200.0, "mg/dL"),
    "cholesterol": (100.0, 200.0, "mg/dL"),
    "triglycerides": (50.0, 150.0, "mg/dL"),
    "hdl": (40.0, 60.0, "mg/dL"),
    "hdl cholesterol": (40.0, 60.0, "mg/dL"),
    "ldl": (70.0, 100.0, "mg/dL"),
    "ldl cholesterol": (70.0, 100.0, "mg/dL"),
    "vldl": (10.0, 30.0, "mg/dL"),
    "total bilirubin": (0.2, 1.2, "mg/dL"),
    "bilirubin": (0.2, 1.2, "mg/dL"),
    "direct bilirubin": (0.0, 0.3, "mg/dL"),
    "sgot": (10.0, 40.0, "U/L"),
    "ast": (10.0, 40.0, "U/L"),
    "sgpt": (7.0, 56.0, "U/L"),
    "alt": (7.0, 56.0, "U/L"),
    "alkaline phosphatase": (44.0, 147.0, "U/L"),
    "tsh": (0.4, 4.5, "uIU/mL"),
    "t3": (0.8, 2.0, "ng/mL"),
    "t4": (5.0, 12.0, "ug/dL"),
    "systolic blood pressure": (90.0, 120.0, "mmHg"),
    "diastolic blood pressure": (60.0, 80.0, "mmHg"),
    "heart rate": (60.0, 100.0, "bpm"),
    "pulse": (60.0, 100.0, "bpm"),
    "spo2": (95.0, 100.0, "%"),
    "oxygen saturation": (95.0, 100.0, "%"),
    "calcium": (8.5, 10.5, "mg/dL"),
    "potassium": (3.5, 5.0, "mmol/L"),
    "sodium": (135.0, 145.0, "mmol/L"),
    "uric acid": (3.5, 7.2, "mg/dL"),
}


def evaluate_abnormality(
    value_numeric: float | None,
    reference_range_text: str | None,
    explicit_flag: str | None = None,
) -> str | None:
    """Determine abnormality flag (normal, low, high, critically_low, critically_high) from explicit flag or range."""
    if explicit_flag:
        fl = explicit_flag.strip().upper()
        if fl in {"LL", "PANIC LOW", "CRITICAL LOW", "CRITICALLY LOW"}:
            return "critically_low"
        if fl in {"HH", "PANIC HIGH", "CRITICAL HIGH", "CRITICALLY HIGH"}:
            return "critically_high"
        if fl in {"CRIT", "CRITICAL", "PANIC"}:
            return "critical"
        if fl in {"H", "HIGH"}:
            return "high"
        if fl in {"L", "LOW"}:
            return "low"
        if fl in {"N", "NORMAL"}:
            return "normal"

    if value_numeric is None or not reference_range_text:
        return None

    m = _RANGE_BOUNDS_RE.search(reference_range_text)
    if m:
        low, high = float(m.group(1)), float(m.group(2))
        spread = high - low
        if value_numeric < low:
            if (spread > 0 and value_numeric <= low - 0.40 * spread) or (low > 0 and value_numeric <= 0.70 * low):
                return "critically_low"
            return "low"
        if value_numeric > high:
            if (spread > 0 and value_numeric >= high + 0.40 * spread) or (high > 0 and value_numeric >= 1.40 * high):
                return "critically_high"
            return "high"
        return "normal"

    m = _RANGE_LT_RE.search(reference_range_text)
    if m:
        upper = float(m.group(1))
        if value_numeric > 1.40 * upper:
            return "critically_high"
        return "high" if value_numeric > upper else "normal"

    m = _RANGE_GT_RE.search(reference_range_text)
    if m:
        lower = float(m.group(1))
        if value_numeric < 0.70 * lower:
            return "critically_low"
        return "low" if value_numeric < lower else "normal"

    return None


# ---------------------------------------------------------------------------
# Candidate Clinical Observation Extraction
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CandidateObservation:
    """Structured candidate extracted from a medical document page."""

    display_name: str
    observation_type: str  # lab_result | vital_sign | measurement
    value_raw: str
    unit_raw: str | None
    value_numeric: float | None
    value_normalized: float | None
    unit_normalized: str | None
    reference_range_text: str | None
    abnormality_flag: str | None
    observed_date: date | None
    source_page: int
    extraction_method: str
    extraction_confidence: float
    provenance_metadata: dict[str, Any] = field(default_factory=dict)


# Known unit token pattern (sorted longest-first inside alternation)
_UNIT_TOKEN_RE = (
    r"10\^[36]/[uµ]L|x10\^[36]/[uµ]L|mill/cumm|cells/cumm|cells/mcL|lakhs/cumm|"
    r"thou/[uµ]L|mg/dL|gm/dL|g/dL|g/L|mmol/L|[uµ]mol/L|mIU/L|[uµ]IU/mL|"
    r"mEq/L|ng/mL|pg/mL|mg/L|IU/L|U/L|mm/hr|mmHg|bpm|/min|/hpf|/cumm|"
    r"fL|pg|kg|lbs|lb|cm|°[CF]|%|sec"
)

# Header / boilerplate lines that should never be parsed as observations
_SKIP_LINE_RE = re.compile(
    r"^\s*(?:patient\s*name|patient\s*id|name\s*:|age\s*/?\s*sex|gender|sex\s*:|"
    r"dob|date\s*of\s*birth|report\s*date|sample\s*collected|collection\s*date|"
    r"test\s*name|investigation|parameter|analyte|specimen|referred\s*by|"
    r"dr\.?\s+|hospital|laboratory|page\s+\d+|phone|email|address|accession|"
    r"end\s+of\s+report|printed\s+on|verified\s+by|signature|uhid|mrn|ipd\s*no|"
    r"date\s*:|collected\s*:|reported\s*:)",
    re.IGNORECASE,
)

# Row pattern 1: Tabular / spaced / colon-separated numeric lab or vital row
# e.g. "Hemoglobin   13.5   g/dL   12.0 - 16.0   N"
# e.g. "Fasting Blood Glucose: 118 mg/dL (70 - 100) [H]"
_NUMERIC_OBS_RE = re.compile(
    rf"^\s*(?P<name>[A-Za-z][A-Za-z0-9\s\-/().,']{{1,65}}?)"
    rf"(?:\s*:\s*|\s{{2,}}|\t+|\s+(?=\d))"
    rf"(?P<val>\d+(?:,\d{{3}})*(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)"
    rf"(?:\s*(?P<unit>{_UNIT_TOKEN_RE}))?"
    rf"(?:\s*[\(\[]?\s*(?P<range>(?:\d+(?:\.\d+)?\s*(?:-|\u2013|to)\s*\d+(?:\.\d+)?|"
    rf"[<>]\s*=?\s*\d+(?:\.\d+)?))\s*[\)\]]?)?"
    rf"(?:\s*(?P<unit_after>{_UNIT_TOKEN_RE}))?"
    rf"(?:\s*[\(\[]?\s*(?P<flag>HIGH|LOW|NORMAL|CRITICAL|CRIT|HH|LL|H|L|N)\s*[\)\]]?)?\s*$",
    re.IGNORECASE,
)

# Row pattern 2: Qualitative / non-numeric lab results (urinalysis, serology, etc.)
# e.g. "Urine Protein   Negative   Negative"
_QUALITATIVE_OBS_RE = re.compile(
    r"^\s*(?P<name>(?:Urine\s+)?[A-Za-z][A-Za-z0-9\s\-/()]{2,55}?)"
    r"(?:\s*:\s*|\s{2,}|\t+)"
    r"(?P<val>Negative|Positive|Trace|Absent|Present|Normal|Reactive|Non[\s-]?Reactive|"
    r"Clear|Turbid|Pale\s+Yellow|Yellow|Amber|Nil|Detected|Not\s+Detected)"
    r"(?:\s{2,}(?P<range>Negative|Absent|Normal|Nil|Non[\s-]?Reactive|Clear|Pale\s+Yellow))?\s*$",
    re.IGNORECASE,
)

_VITAL_KEYWORDS = (
    "blood pressure",
    "bp",
    "heart rate",
    "pulse",
    "temperature",
    "temp",
    "spo2",
    "oxygen saturation",
    "respiratory rate",
    "weight",
    "height",
    "bmi",
)


def _clean_test_name(raw_name: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw_name).strip(" :-•*\t")
    return cleaned


def _is_valid_test_name(name: str) -> bool:
    if len(name) < 2 or len(name) > 80:
        return False
    # Reject pure numbers or date-like tokens
    if re.fullmatch(r"[\d\s/\-.]+", name):
        return False
    # Reject lines that look like full sentences (> 7 words)
    if len(name.split()) > 7:
        return False
    return True


def _infer_observation_type(name: str) -> str:
    nl = name.lower()
    if any(k in nl for k in _VITAL_KEYWORDS):
        return "vital_sign"
    return "lab_result"


def _try_parse_numeric(val_raw: str) -> float | None:
    if "/" in val_raw:
        return None
    try:
        return float(val_raw.replace(",", "").strip())
    except ValueError:
        return None


def parse_candidate_observations(
    sanitized_text: str,
    *,
    page_number: int,
    extraction_method: str,
    page_confidence: float | None = None,
    document_date: date | None = None,
) -> list[CandidateObservation]:
    """
    Parse structured candidate lab/vital observations from one page of sanitized text.
    Deduplicates identical (name, value_raw) pairs on the same page.
    """
    candidates: list[CandidateObservation] = []
    seen: set[tuple[str, str]] = set()
    base_conf = page_confidence if page_confidence is not None else 0.85

    for line_idx, raw_line in enumerate(sanitized_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or len(line) < 4:
            continue
        if _SKIP_LINE_RE.match(line):
            continue

        # 1. Try numeric / ratio (e.g. BP 122/78) observation pattern
        m = _NUMERIC_OBS_RE.match(line)
        if m:
            name = _clean_test_name(m.group("name"))
            val_raw = m.group("val").strip()
            unit_raw = m.group("unit") or m.group("unit_after")
            ref_range = m.group("range").strip() if m.group("range") else None
            explicit_flag = m.group("flag")

            # Require at least a unit, reference range, BP slash, or known vital keyword
            # so stray numbered headings ("1. Discharge Plan") are never misparsed as labs
            has_clinical_anchor = bool(
                unit_raw
                or ref_range
                or "/" in val_raw
                or any(k in name.lower() for k in _VITAL_KEYWORDS)
                or any(
                    k in name.lower()
                    for k in (
                        "hemoglobin",
                        "haemoglobin",
                        "wbc",
                        "rbc",
                        "platelet",
                        "glucose",
                        "hba1c",
                        "creatinine",
                        "urea",
                        "bilirubin",
                        "cholesterol",
                        "triglyceride",
                        "ldl",
                        "hdl",
                        "tsh",
                        "alt",
                        "ast",
                        "sgpt",
                        "sgot",
                        "sodium",
                        "potassium",
                        "calcium",
                        "ph",
                        "specific gravity",
                    )
                )
            )
            if not _is_valid_test_name(name) or not has_clinical_anchor:
                continue

            dedup_key = (name.lower(), val_raw)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            val_num = _try_parse_numeric(val_raw)
            val_norm, unit_norm = normalize_unit_and_value(name, val_num, unit_raw)

            # If reference range is missing from OCR, look up standard clinical reference interval
            if not ref_range:
                low_name = name.lower().strip()
                for key, (d_low, d_high, d_unit) in DEFAULT_BIOMARKER_RANGES.items():
                    if key in low_name or low_name in key:
                        ref_range = f"{d_low} - {d_high} {d_unit}"
                        if not unit_raw:
                            unit_raw = d_unit
                        break

            abn = evaluate_abnormality(val_num, ref_range, explicit_flag)

            # Confidence boost when unit + reference range both matched cleanly
            conf = base_conf
            if unit_raw and ref_range:
                conf = min(0.99, base_conf * 0.98)
            elif unit_raw or ref_range:
                conf = min(0.95, base_conf * 0.92)
            else:
                conf = min(0.85, base_conf * 0.82)

            candidates.append(
                CandidateObservation(
                    display_name=name,
                    observation_type=_infer_observation_type(name),
                    value_raw=val_raw,
                    unit_raw=unit_raw.strip() if unit_raw else None,
                    value_numeric=val_num,
                    value_normalized=val_norm,
                    unit_normalized=unit_norm,
                    reference_range_text=ref_range,
                    abnormality_flag=abn,
                    observed_date=document_date,
                    source_page=page_number,
                    extraction_method=f"{extraction_method}+regex_lab_v1",
                    extraction_confidence=round(conf, 3),
                    provenance_metadata={
                        "line_number": line_idx,
                        "raw_line": line[:300],
                        "parser": "numeric_lab_v1",
                    },
                )
            )
            continue

        # 2. Try qualitative / non-numeric observation pattern
        mq = _QUALITATIVE_OBS_RE.match(line)
        if mq:
            name = _clean_test_name(mq.group("name"))
            val_raw = mq.group("val").strip()
            ref_range = mq.group("range").strip() if mq.group("range") else None
            if not _is_valid_test_name(name):
                continue

            dedup_key = (name.lower(), val_raw.lower())
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            abn: str | None = None
            if val_raw.lower() in {"positive", "reactive", "detected", "present"}:
                abn = "high"
            elif val_raw.lower() in {
                "negative",
                "non-reactive",
                "non reactive",
                "absent",
                "nil",
                "normal",
            }:
                abn = "normal"

            candidates.append(
                CandidateObservation(
                    display_name=name,
                    observation_type="lab_result",
                    value_raw=val_raw,
                    unit_raw=None,
                    value_numeric=None,
                    value_normalized=None,
                    unit_normalized=None,
                    reference_range_text=ref_range,
                    abnormality_flag=abn,
                    observed_date=document_date,
                    source_page=page_number,
                    extraction_method=f"{extraction_method}+regex_qual_v1",
                    extraction_confidence=round(min(0.92, base_conf * 0.90), 3),
                    provenance_metadata={
                        "line_number": line_idx,
                        "raw_line": line[:300],
                        "parser": "qualitative_lab_v1",
                    },
                )
            )

    return candidates


def parse_iso_or_date_string(value: str | None) -> date | None:
    """Helper to parse ISO dates safely."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return parse_single_date(value)
