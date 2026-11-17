"""
Deterministic Clinical Safety & Triage Layer (Phase 6 — AIR-004).

ZERO-TOLERANCE SAFETY INVARIANTS:
1. Emergency red flags are caught deterministically BEFORE any LLM call and return
   immediate urgent care / emergency helpline guidance (India 112 / 108 + international).
2. Requests to diagnose, prescribe new medications, or stop/change medication dosages
   are deterministically guarded with a clear informational boundary.
3. Post-LLM output scanning catches any unsafe prescribing/diagnosis directives from
   small local models and replaces them with a safe boundary response.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

SafetyLevel = Literal["normal", "boundary_refusal", "emergency_escalation"]

# Negation guard so "no chest pain" or "without difficulty breathing" doesn't falsely escalate
_NEGATION_PREFIX_RE = re.compile(
    r"\b(?:no|not|never|without|denies?|denied|zero|absent)\s+(?:\w+\s+){0,2}$",
    re.IGNORECASE,
)

# --- Tier 1: Emergency Red Flags (Pre-LLM immediate escalation) ---

_EMERGENCY_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "self_harm_crisis",
        "mental_health_crisis",
        re.compile(
            r"\b(want\s+to\s+(?:die|kill\s+myself|end\s+my\s+life)|"
            r"suicid(?:al|e)|overdose\s+on\s+my\s+pills|"
            r"hurt(?:ing)?\s+myself|self[\s-]?harm\s+right\s+now)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "cardiac_emergency",
        "medical_emergency",
        re.compile(
            r"\b((?:severe|crushing|tight|sudden|radiating)\s+chest\s+pain|"
            r"chest\s+pain\b.*\b(?:shortness\s+of\s+breath|sweating|left\s+arm|jaw|dizzy)|"
            r"heart\s+attack\s+symptoms?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "stroke_red_flag",
        "medical_emergency",
        re.compile(
            r"\b(face\s+(?:is\s+)?drooping|facial\s+droop|"
            r"sudden(?:ly)?\s+slurred\s+speech|speech\s+(?:is\s+)?slurred|"
            r"slurred\s+speech\s+and\s+(?:weakness|numbness)|"
            r"(?:can'?t|cannot)\s+(?:move|lift)\s+(?:my|one)\s+(?:left\s+|right\s+)?(?:arm|leg|side)|"
            r"worst\s+headache\s+of\s+my\s+life)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "respiratory_anaphylaxis",
        "medical_emergency",
        re.compile(
            r"\b(can'?t\s+breathe|cannot\s+breathe|gasping\s+for\s+air|"
            r"throat\s+(?:is\s+)?(?:closing|swelling)|tongue\s+(?:is\s+)?swelling|"
            r"lips?\s+turning\s+blue|anaphylaxis|severe\s+allergic\s+reaction)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "acute_bleeding_or_neuro",
        "medical_emergency",
        re.compile(
            r"\b(uncontrolled\s+bleeding|won'?t\s+stop\s+bleeding|"
            r"vomiting\s+blood|coughing\s+up\s+blood|"
            r"having\s+a\s+seizure|passed\s+out|unconscious)\b",
            re.IGNORECASE,
        ),
    ),
]

# --- Tier 2: Clinical Boundary Rules (No Diagnosis / No Prescribing / No Dosage Changes) ---

_BOUNDARY_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "medication_dosage_change",
        re.compile(
            r"\b((?:should|can)\s+i\s+(?:stop\s+taking|skip|double|triple|increase|decrease|"
            r"reduce|change|adjust)\s+(?:my\s+)?(?:medication|medicine|dose|dosage|pills?|"
            r"tablets?|insulin|metformin|statin|blood\s+pressure|antidepressant|steroid|"
            r"antibiotic|thyroxine)|"
            r"tell\s+me\s+(?:what|how\s+much)\s+dose\s+to\s+take)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "prescription_request",
        re.compile(
            r"\b(prescribe\s+(?:me|a\s+)|write\s+(?:me\s+)?a\s+prescription|"
            r"which\s+(?:antibiotic|medicine|drug|tablet|medication)\s+should\s+i\s+"
            r"(?:buy|start|take)\s+for)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "definitive_diagnosis_demand",
        re.compile(
            r"\b(diagnose\s+(?:me|my)|confirm\s+(?:whether|if)\s+i\s+have|"
            r"tell\s+me\s+definitively\s+(?:what\s+disease|if\s+i\s+have))\b",
            re.IGNORECASE,
        ),
    ),
]

# --- Post-LLM Output Safety Filter ---

_UNSAFE_OUTPUT_RE = re.compile(
    r"\b(you\s+should\s+(?:stop\s+taking|double\s+your\s+dose|increase\s+your\s+dose|"
    r"start\s+taking\s+\d+\s*(?:mg|mcg|ml))|"
    r"i\s+(?:diagnose\s+you\s+with|prescribe\s+you|recommend\s+stopping\s+your\s+medication)|"
    r"stop\s+your\s+(?:insulin|blood\s+pressure|heart)\s+medication\s+immediately)\b",
    re.IGNORECASE,
)

INFORMATIONAL_DISCLAIMER = (
    "MEDIFLOW provides informational health-record support only. It does not diagnose "
    "conditions, prescribe medications, or replace licensed medical care."
)

EMERGENCY_MEDICAL_RESPONSE = (
    "Your message describes symptoms that could indicate a medical emergency. "
    "Please seek immediate emergency medical care right now:\n\n"
    "- Call **112** (national emergency helpline in India) or **108** (ambulance), "
    "or your local emergency number (such as 911 / 999).\n"
    "- Go to the nearest emergency department immediately — do not drive yourself if you "
    "feel dizzy, faint, or short of breath.\n\n"
    "MEDIFLOW is an informational health record tool and cannot provide emergency medical care."
)

MENTAL_HEALTH_CRISIS_RESPONSE = (
    "It sounds like you may be going through a very difficult moment, and you deserve "
    "immediate, compassionate human support right now:\n\n"
    "- **India Tele-MANAS (24/7 Free Helpline):** Call **14416** or **1-800-891-4416**\n"
    "- **Emergency Services:** Call **112** (India) or your local emergency line "
    "(e.g., **988** in the US/Canada)\n"
    "- Please reach out to a trusted family member, friend, or nearby hospital ER.\n\n"
    "You do not have to face this alone. Please contact one of these crisis services right away."
)


@dataclass(slots=True)
class SafetyAssessment:
    """Result of deterministic pre-LLM clinical safety triage."""

    safety_level: SafetyLevel
    rule_id: str | None = None
    override_reply: str | None = None
    clarifying_questions: list[str] | None = None


def evaluate_user_message_safety(message: str) -> SafetyAssessment:
    """
    Deterministically evaluate an incoming patient message before any LLM call.
    Returns:
    - emergency_escalation: immediate fixed emergency guidance (bypasses LLM)
    - boundary_refusal: flags prescribing/dosage/diagnosis request for safe boundary handling
    - normal: safe to proceed with patient-record-grounded informational Q&A
    """
    text = message.strip()

    for rule_id, category, pattern in _EMERGENCY_RULES:
        for match in pattern.finditer(text):
            # Ignore negated expressions like "no chest pain" for medical symptoms
            prefix = text[max(0, match.start() - 32) : match.start()]
            if category != "mental_health_crisis" and _NEGATION_PREFIX_RE.search(prefix):
                continue
            reply = (
                MENTAL_HEALTH_CRISIS_RESPONSE
                if category == "mental_health_crisis"
                else EMERGENCY_MEDICAL_RESPONSE
            )
            return SafetyAssessment(
                safety_level="emergency_escalation",
                rule_id=rule_id,
                override_reply=reply,
                clarifying_questions=[],
            )

    for rule_id, pattern in _BOUNDARY_RULES:
        if pattern.search(text):
            return SafetyAssessment(
                safety_level="boundary_refusal",
                rule_id=rule_id,
                override_reply=build_boundary_refusal_reply(rule_id),
                clarifying_questions=[
                    "Would you like me to summarize your recent lab results or history "
                    "to share with your doctor?",
                    "Would you like help drafting questions for your upcoming clinician visit?",
                ],
            )

    return SafetyAssessment(safety_level="normal")


def build_boundary_refusal_reply(rule_id: str) -> str:
    """Deterministic safe informational refusal for diagnosis/prescribing/dosage requests."""
    if rule_id == "medication_dosage_change":
        return (
            "I cannot recommend starting, stopping, or changing the dosage of any medication. "
            "Adjusting prescription doses without clinician supervision can be unsafe. "
            "Please consult your prescribing doctor or pharmacist before making any changes. "
            "If you'd like, I can review your recorded observations or help you prepare "
            "questions for your doctor."
        )
    if rule_id == "prescription_request":
        return (
            "I cannot prescribe medications or recommend a specific drug to take. "
            "Only a licensed healthcare professional who can evaluate your full clinical picture "
            "should recommend or prescribe treatment. I can, however, summarize your stored "
            "allergies, conditions, or recent lab trends to bring to your appointment."
        )
    return (
        "I cannot provide a medical diagnosis or confirm whether you have a specific condition. "
        "I can help organize your symptoms, explain terms from your uploaded reports, and "
        "prepare questions to discuss with a qualified healthcare professional."
    )


def enforce_safe_assistant_reply(reply: str, *, pre_level: SafetyLevel) -> tuple[str, SafetyLevel]:
    """
    Post-LLM output filter: if a local model emits an unsafe prescribing/dosage/diagnosis
    directive, intercept and replace it deterministically (AIR-004 defense-in-depth).
    """
    if pre_level == "emergency_escalation":
        return reply, "emergency_escalation"

    if _UNSAFE_OUTPUT_RE.search(reply):
        return (
            build_boundary_refusal_reply("medication_dosage_change"),
            "boundary_refusal",
        )
    return reply, pre_level
