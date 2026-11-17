"""
Pluggable OCR Backend Abstraction.
Default implementation: RapidOcrBackend (Apache-2.0 PaddleOCR ONNX models, zero OS binary).
Optional fallback adapter: TesseractBackend (only used if explicitly configured & installed).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class OcrBox:
    """Single OCR detected text region with bounding box and confidence."""

    text: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    @property
    def y_center(self) -> float:
        return (self.y_min + self.y_max) / 2.0

    @property
    def height(self) -> float:
        return max(1.0, self.y_max - self.y_min)


@dataclass(slots=True)
class OcrResult:
    """Structured output from an OCR backend for a single page/image."""

    text: str
    mean_confidence: float | None
    boxes: list[OcrBox]
    backend_name: str


class OcrBackend(Protocol):
    """Protocol for pluggable local OCR engines."""

    name: str

    def recognize(self, image_bgr: np.ndarray) -> OcrResult:
        """Run OCR on a BGR numpy image and return reading-order text + boxes."""
        ...


def reconstruct_lines(boxes: list[OcrBox]) -> str:
    """
    Group OCR bounding boxes into horizontal visual lines by vertical overlap / Y-center
    proximity, then sort tokens left-to-right within each line.
    Preserves lab-report table rows like 'Hemoglobin   13.5   g/dL   12.0 - 16.0'.
    """
    if not boxes:
        return ""

    sorted_boxes = sorted(boxes, key=lambda b: (b.y_center, b.x_min))
    lines: list[list[OcrBox]] = []

    for box in sorted_boxes:
        placed = False
        for line in lines:
            ref = line[0]
            avg_h = (ref.height + box.height) / 2.0
            if abs(box.y_center - ref.y_center) <= max(avg_h * 0.55, 8.0):
                line.append(box)
                placed = True
                break
        if not placed:
            lines.append([box])

    # Sort lines top-to-bottom and tokens left-to-right
    lines.sort(key=lambda ln: min(b.y_center for b in ln))
    rendered: list[str] = []
    for line in lines:
        line.sort(key=lambda b: b.x_min)
        parts: list[str] = []
        prev_x_max: float | None = None
        for b in line:
            token = b.text.strip()
            if not token:
                continue
            if prev_x_max is not None:
                gap = b.x_min - prev_x_max
                # Preserve visual column separation with two spaces for downstream table parsing
                sep = "  " if gap > max(b.height * 0.9, 14.0) else " "
                parts.append(sep + token)
            else:
                parts.append(token)
            prev_x_max = b.x_max
        if parts:
            rendered.append("".join(parts))

    return "\n".join(rendered)


@lru_cache(maxsize=1)
def _load_rapidocr_engine() -> Any:
    """Lazy-load RapidOCR ONNX engine once per process to conserve RAM."""
    from rapidocr_onnxruntime import RapidOCR

    logger.info("rapidocr_engine_initializing")
    return RapidOCR()


# Sorted strictly longest-first as a tuple for 100% deterministic replacement
# (prevents shorter suffixes like 'U/L' from corrupting 'mIU/L' across PYTHONHASHSEED runs)
_OCR_PROTECTED_TOKENS: tuple[str, ...] = tuple(
    sorted(
        (
            "HbA1c",
            "g/dL",
            "mg/dL",
            "gm/dL",
            "mmol/L",
            "umol/L",
            "mIU/L",
            "uIU/mL",
            "mEq/L",
            "ng/mL",
            "pg/mL",
            "mg/L",
            "IU/L",
            "U/L",
            "mmHg",
            "SpO2",
            "fL",
        ),
        key=len,
        reverse=True,
    )
)

_UNIT_GLUE_RE = re.compile(
    r"(\d)(g/dL|mg/dL|gm/dL|g/L|mmol/L|umol/L|mIU/L|uIU/mL|mEq/L|ng/mL|pg/mL|"
    r"mg/L|IU/L|U/L|mmHg|bpm|10\^[36]/uL)\b"
)

# Common ALL-CAPS medical document header words that CJK+EN OCR occasionally glues together
_ALLCAPS_HEADER_WORDS_RE = re.compile(
    r"(?<=[A-Z])(LABORATORY|REPORT|DIAGNOSTIC|HOSPITAL|DISCHARGE|SUMMARY|"
    r"PRESCRIPTION|RADIOLOGY|CLINICAL|CONSULTATION|PATHOLOGY|COMPLETE|BLOOD|COUNT|PANEL)"
)


def normalize_ocr_text(text: str) -> str:
    """
    Normalize OCR output for medical document readability & downstream parsing:
    1. Unicode NFKC normalization (converts full-width CJK punctuation to standard ASCII).
    2. Restores spacing glued by CJK+EN OCR models (CamelCase medical terms, colons, units, parens)
       while protecting canonical clinical tokens like HbA1c, g/dL, mIU/L, mmHg.
    """
    if not text:
        return ""

    # 1. Normalize full-width unicode punctuation to standard ASCII
    norm = unicodedata.normalize("NFKC", text)

    out_lines: list[str] = []
    for line in norm.splitlines():
        # Protect known mixed-case clinical units/tokens with placeholders
        placeholders: dict[str, str] = {}
        working = line
        for idx, token in enumerate(_OCR_PROTECTED_TOKENS):
            if token in working:
                key = f"__TOK{idx}__"
                placeholders[key] = token
                working = working.replace(token, key)

        # Insert space between camel-cased words (e.g. FastingBloodGlucose -> Fasting Blood Glucose)
        working = re.sub(r"([a-z])([A-Z])", r"\1 \2", working)
        # Split glued ALL-CAPS medical header tokens (e.g. LABORATORYREPORT -> LABORATORY REPORT)
        working = _ALLCAPS_HEADER_WORDS_RE.sub(r" \1", working)
        # Insert space after colon before non-space (excluding timestamps like 12:30)
        working = re.sub(r":(?=\S)", ": ", working)
        working = re.sub(r"(\d): (\d{2})\b", r"\1:\2", working)
        # Insert space before opening parenthesis when glued to a token
        working = re.sub(r"(?<=[^\s\(])\(", " (", working)

        # Restore protected clinical tokens
        for key, token in placeholders.items():
            working = working.replace(key, token)

        # Separate numeric values glued directly to units (e.g. 14.2g/dL -> 14.2 g/dL)
        working = _UNIT_GLUE_RE.sub(r"\1 \2", working)
        # Normalize spaces around range hyphens inside parens (12.0-16.0 -> 12.0 - 16.0)
        working = re.sub(r"\((\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\)", r"(\1 - \2)", working)
        working = re.sub(r"\(<(\d+(?:\.\d+)?)\)", r"(< \1)", working)
        working = re.sub(r"\(>(\d+(?:\.\d+)?)\)", r"(> \1)", working)
        out_lines.append(working)

    return "\n".join(out_lines)


class RapidOcrBackend:
    """Default CPU-friendly ONNX PaddleOCR backend (zero native OS binaries)."""

    name: str = "rapidocr"

    def recognize(self, image_bgr: np.ndarray) -> OcrResult:
        engine = _load_rapidocr_engine()
        raw_result, _elapse = engine(image_bgr)
        boxes: list[OcrBox] = []
        confidences: list[float] = []

        if raw_result:
            for item in raw_result:
                # RapidOCR returns [polygon_4pts, text, score]
                polygon, text, score = item[0], str(item[1]), float(item[2])
                xs = [float(pt[0]) for pt in polygon]
                ys = [float(pt[1]) for pt in polygon]
                boxes.append(
                    OcrBox(
                        text=text,
                        confidence=score,
                        x_min=min(xs),
                        y_min=min(ys),
                        x_max=max(xs),
                        y_max=max(ys),
                    )
                )
                confidences.append(score)

        text = normalize_ocr_text(reconstruct_lines(boxes))
        mean_conf = round(sum(confidences) / len(confidences), 4) if confidences else None
        return OcrResult(
            text=text,
            mean_confidence=mean_conf,
            boxes=boxes,
            backend_name=self.name,
        )


def get_default_ocr_backend() -> OcrBackend:
    """Return the configured default OCR backend."""
    return RapidOcrBackend()
