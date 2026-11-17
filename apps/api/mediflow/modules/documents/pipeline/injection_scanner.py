"""
SEC-011: Document Prompt Injection Scanner & Containment.
Detects adversarial prompt-injection instructions embedded inside untrusted medical
documents (PDF text / OCR output), flags them for audit metadata, and produces a
sanitized text view for downstream parsers while keeping raw text explicitly marked
as untrusted data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_INJECTION_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "instruction_override",
        re.compile(
            r"\b(ignore|disregard|forget|override)\s+(all\s+)?"
            r"(previous|prior|above|system|earlier)\s+"
            r"(instructions?|prompts?|rules?|directives?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "system_prompt_exfiltration",
        re.compile(
            r"\b(reveal|output|print|dump|show|expose)\s+(the\s+)?"
            r"(system\s+prompt|hidden\s+instructions?|all\s+patient\s+records?|"
            r"other\s+patients?|database|api\s+keys?|secrets?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "role_hijack",
        re.compile(
            r"\b(you\s+are\s+now|act\s+as\s+(a\s+)?(root|admin|developer|unrestricted)|"
            r"new\s+system\s+instruction|developer\s+mode)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tool_or_sql_injection",
        re.compile(
            r"\b(execute\s+sql|run\s+sql|drop\s+table|select\s+\*\s+from\s+users|"
            r"call\s+tool|delete\s+all\s+records?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "clinical_safety_bypass",
        re.compile(
            r"\b(prescribe\s+immediately|tell\s+the\s+patient\s+to\s+stop\s+taking|"
            r"bypass\s+safety|ignore\s+medical\s+safety)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "delimiter_spoofing",
        re.compile(
            r"(<\s*/?\s*system\s*>|\[SYSTEM\]|###\s*SYSTEM\s*INSTRUCTION)",
            re.IGNORECASE,
        ),
    ),
]


@dataclass(slots=True)
class InjectionFinding:
    """Single prompt-injection pattern match detected in document text."""

    rule_id: str
    page_number: int
    matched_snippet: str


@dataclass(slots=True)
class InjectionScanResult:
    """Summary of SEC-011 scan across one or more pages."""

    flagged: bool
    findings: list[InjectionFinding]
    sanitized_text: str


def scan_page_text(raw_text: str, page_number: int) -> InjectionScanResult:
    """
    Scan extracted page text for embedded prompt-injection instructions.
    Neutralizes matching lines in `sanitized_text` so structured parsers skip
    malicious lines without corrupting legitimate clinical observations.
    """
    findings: list[InjectionFinding] = []
    sanitized_lines: list[str] = []

    for line in raw_text.splitlines():
        line_flagged = False
        for rule_id, pattern in _INJECTION_RULES:
            match = pattern.search(line)
            if match:
                findings.append(
                    InjectionFinding(
                        rule_id=rule_id,
                        page_number=page_number,
                        matched_snippet=match.group(0)[:160],
                    )
                )
                line_flagged = True
        if not line_flagged:
            sanitized_lines.append(line)

    return InjectionScanResult(
        flagged=len(findings) > 0,
        findings=findings,
        sanitized_text="\n".join(sanitized_lines),
    )
