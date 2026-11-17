"""
Deterministic Medical Document Classifier.
Classifies extracted document text into MEDIFLOW's canonical DocumentType categories
using weighted clinical keywords, header signals, and structural patterns.
Zero paid APIs, fast on CPU, fully explainable & reproducible.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mediflow.modules.documents.schemas import DocumentType


@dataclass(slots=True)
class ClassificationResult:
    """Predicted document category with normalized confidence and matched signals."""

    document_type: DocumentType
    confidence: float
    scores: dict[str, float]
    matched_signals: list[str]


# (weight, compiled regex, signal label)
_CATEGORY_RULES: dict[DocumentType, list[tuple[float, re.Pattern[str], str]]] = {
    "lab_report": [
        (
            3.5,
            re.compile(
                r"\b(laboratory\s+report|lab\s+report|pathology\s+report|diagnostic\s+report)\b",
                re.I,
            ),
            "lab_header",
        ),
        (
            3.0,
            re.compile(
                r"\b(complete\s+blood\s+count|cbc|metabolic\s+panel|lipid\s+profile|thyroid\s+profile|urinalysis|urine\s+routine)\b",
                re.I,
            ),
            "panel_name",
        ),
        (
            2.5,
            re.compile(
                r"\b(reference\s+range|biological\s+ref|normal\s+range|ref\.?\s*interval)\b", re.I
            ),
            "reference_range_col",
        ),
        (
            2.0,
            re.compile(
                r"\b(hemoglobin|haemoglobin|wbc|rbc|platelets|hba1c|creatinine|glucose|cholesterol|bilirubin|sgpt|sgot|alt|ast|tsh)\b",
                re.I,
            ),
            "biomarker_terms",
        ),
        (
            1.5,
            re.compile(r"\b(mg/dl|g/dl|mmol/l|miu/l|u/l|10\^3/ul|cells/mcl|fL|pg)\b", re.I),
            "lab_units",
        ),
        (
            1.5,
            re.compile(r"\b(sample\s+collected|specimen|accession\s+no|lab\s+id)\b", re.I),
            "specimen_meta",
        ),
    ],
    "prescription": [
        (4.0, re.compile(r"\b(prescription|rx\b|r/x\b)\b", re.I), "rx_header"),
        (
            2.5,
            re.compile(r"\b(tab\.|cap\.|syp\.|inj\.|oint\.|tablet|capsule|syrup)\b", re.I),
            "dosage_form",
        ),
        (
            2.5,
            re.compile(
                r"\b(once\s+daily|twice\s+daily|thrice\s+daily|od\b|bd\b|tds\b|qid\b|hs\b|sos\b|before\s+food|after\s+food|for\s+\d+\s+days)\b",
                re.I,
            ),
            "sig_frequency",
        ),
        (2.0, re.compile(r"\b(mg|mcg|ml)\s+(po|oral|od|bd|tds|daily)\b", re.I), "dose_instruction"),
        (
            1.5,
            re.compile(r"\b(dispense|refills?|pharmacist|prescribed\s+by)\b", re.I),
            "pharmacy_terms",
        ),
    ],
    "discharge_summary": [
        (
            4.5,
            re.compile(r"\b(discharge\s+summary|hospital\s+discharge|inpatient\s+summary)\b", re.I),
            "discharge_header",
        ),
        (
            2.5,
            re.compile(
                r"\b(date\s+of\s+admission|admission\s+date|date\s+of\s+discharge|discharge\s+date)\b",
                re.I,
            ),
            "admission_discharge_dates",
        ),
        (
            2.5,
            re.compile(
                r"\b(hospital\s+course|course\s+in\s+hospital|condition\s+at\s+discharge|discharge\s+medications?)\b",
                re.I,
            ),
            "hospital_course",
        ),
        (
            2.0,
            re.compile(
                r"\b(final\s+diagnosis|principal\s+diagnosis|discharge\s+instructions|follow[\s-]?up\s+plan)\b",
                re.I,
            ),
            "discharge_sections",
        ),
        (
            1.5,
            re.compile(r"\b(ipd\s+no|ward|attending\s+physician|admitting\s+diagnosis)\b", re.I),
            "inpatient_meta",
        ),
    ],
    "imaging": [
        (
            4.5,
            re.compile(
                r"\b(radiology\s+report|imaging\s+report|x[\s-]?ray\s+report|ct\s+scan|mri\s+report|ultrasound\s+report|usg\s+report|sonography)\b",
                re.I,
            ),
            "imaging_header",
        ),
        (
            3.0,
            re.compile(
                r"\b(chest\s+x[\s-]?ray|pa\s+view|ap\s+view|axial\s+sections|t1[\s-]?weighted|t2[\s-]?weighted|doppler)\b",
                re.I,
            ),
            "modality_terms",
        ),
        (
            2.5,
            re.compile(r"\b(findings\s*:|impression\s*:|technique\s*:|comparison\s*:)\b", re.I),
            "radiology_structure",
        ),
        (
            2.0,
            re.compile(
                r"\b(cardiothoracic|lung\s+fields|costophrenic|mediastinum|parenchyma|no\s+acute\s+cardiopulmonary|radiologist)\b",
                re.I,
            ),
            "radiology_anatomy",
        ),
    ],
    "clinical_note": [
        (
            3.5,
            re.compile(
                r"\b(consultation\s+note|progress\s+note|clinical\s+note|opd\s+note|outpatient\s+note|soap\s+note)\b",
                re.I,
            ),
            "clinical_note_header",
        ),
        (
            2.5,
            re.compile(
                r"\b(chief\s+complaint|history\s+of\s+present\s+illness|hpi\s*:|physical\s+examination|assessment\s+and\s+plan)\b",
                re.I,
            ),
            "soap_structure",
        ),
        (
            1.5,
            re.compile(
                r"\b(vital\s+signs|bp\s*:|pulse\s*:|spo2|follow[\s-]?up\s+visit|review\s+of\s+systems)\b",
                re.I,
            ),
            "opd_exam",
        ),
    ],
    "insurance": [
        (
            4.0,
            re.compile(
                r"\b(health\s+insurance|policy\s+number|claim\s+number|tpa\b|cashless\s+approval|reimbursement\s+claim|sum\s+insured)\b",
                re.I,
            ),
            "insurance_header",
        ),
        (
            2.0,
            re.compile(
                r"\b(premium|policyholder|pre[\s-]?authorization|co[\s-]?pay|deductible|insured\s+member)\b",
                re.I,
            ),
            "insurance_terms",
        ),
    ],
}


def classify_document(text: str, filename: str = "") -> ClassificationResult:
    """
    Classify a medical document into one of MEDIFLOW's canonical DocumentType values.
    Combines extracted text with weak filename hints when text is sparse.
    """
    combined = f"{filename}\n{text}" if filename else text
    scores: dict[str, float] = dict.fromkeys(_CATEGORY_RULES, 0.0)
    signals_by_cat: dict[str, list[str]] = {cat: [] for cat in _CATEGORY_RULES}

    for category, rules in _CATEGORY_RULES.items():
        for weight, pattern, signal_name in rules:
            matches = pattern.findall(combined)
            if matches:
                # Cap repeated-match bonus so one dense word doesn't overpower headers
                multiplier = 1.0 + min(len(matches) - 1, 3) * 0.25
                scores[category] += round(weight * multiplier, 3)
                signals_by_cat[category].append(signal_name)

    best_cat: DocumentType = "other"
    best_score = 0.0
    total_score = sum(scores.values())

    for cat, val in scores.items():
        if val > best_score:
            best_score = val
            best_cat = cat  # type: ignore[assignment]

    if best_score < 2.0:
        return ClassificationResult(
            document_type="other",
            confidence=0.4 if total_score == 0 else round(max(0.35, 1.0 - best_score / 4.0), 3),
            scores=scores,
            matched_signals=[],
        )

    # Confidence blends share of total signal and absolute signal strength
    share = best_score / total_score if total_score > 0 else 0.0
    strength = min(1.0, best_score / 9.0)
    confidence = round(min(0.99, 0.5 * share + 0.5 * strength), 3)

    return ClassificationResult(
        document_type=best_cat,
        confidence=confidence,
        scores=scores,
        matched_signals=signals_by_cat[best_cat],
    )
