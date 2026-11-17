"""
Page-Anchored Document Chunker.
Splits extracted multi-page medical text into clean, overlapping chunks while preserving
section headings and exact page spans (page_start..page_end) for Phase 7 RAG citations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SECTION_HEADING_RE = re.compile(
    r"^\s*(?:[A-Z][A-Z0-9\s\-/]{3,45}:?|"
    r"(?:Findings|Impression|Diagnosis|Final Diagnosis|Discharge Medications|"
    r"Hospital Course|Chief Complaint|Assessment and Plan|Complete Blood Count|"
    r"Metabolic Panel|Lipid Profile|Urinalysis|Vital Signs|Prescription)\s*:?)\s*$",
    re.IGNORECASE,
)


@dataclass(slots=True)
class TextChunk:
    """A single page-anchored chunk ready for DocumentChunk persistence."""

    chunk_index: int
    page_start: int
    page_end: int
    content: str
    token_estimate: int
    section_heading: str | None


def _estimate_tokens(text: str) -> int:
    """Fast deterministic token estimate (~4 chars/token)."""
    return max(1, (len(text) + 3) // 4)


def build_document_chunks(
    pages: list[tuple[int, str]],
    *,
    max_chars: int = 1200,
    overlap_chars: int = 150,
) -> list[TextChunk]:
    """
    Build page-anchored text chunks from [(page_number, sanitized_text), ...].
    Respects line boundaries so lab rows are never split mid-number.
    """
    chunks: list[TextChunk] = []
    current_lines: list[str] = []
    current_len = 0
    chunk_page_start: int | None = None
    chunk_page_end: int | None = None
    current_heading: str | None = None
    chunk_idx = 0

    def _flush() -> None:
        nonlocal current_lines, current_len, chunk_page_start, chunk_page_end, chunk_idx
        if not current_lines or chunk_page_start is None or chunk_page_end is None:
            return
        content = "\n".join(current_lines).strip()
        if not content:
            current_lines = []
            current_len = 0
            return
        chunks.append(
            TextChunk(
                chunk_index=chunk_idx,
                page_start=chunk_page_start,
                page_end=chunk_page_end,
                content=content,
                token_estimate=_estimate_tokens(content),
                section_heading=current_heading,
            )
        )
        chunk_idx += 1

        # Keep trailing overlap lines up to overlap_chars
        if overlap_chars > 0:
            overlap: list[str] = []
            acc = 0
            for ln in reversed(current_lines):
                if acc + len(ln) > overlap_chars and overlap:
                    break
                overlap.append(ln)
                acc += len(ln) + 1
            overlap.reverse()
            current_lines = overlap
            current_len = sum(len(x) + 1 for x in current_lines)
            chunk_page_start = chunk_page_end
        else:
            current_lines = []
            current_len = 0
            chunk_page_start = None
            chunk_page_end = None

    for page_num, text in pages:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if _SECTION_HEADING_RE.match(line) and len(line) <= 60:
                current_heading = line.rstrip(":")

            if chunk_page_start is None:
                chunk_page_start = page_num
            chunk_page_end = page_num

            if current_len + len(line) + 1 > max_chars and current_lines:
                _flush()
                if chunk_page_start is None:
                    chunk_page_start = page_num
                chunk_page_end = page_num

            current_lines.append(line)
            current_len += len(line) + 1

    # Flush final chunk
    if current_lines and chunk_page_start is not None and chunk_page_end is not None:
        content = "\n".join(current_lines).strip()
        if content:
            chunks.append(
                TextChunk(
                    chunk_index=chunk_idx,
                    page_start=chunk_page_start,
                    page_end=chunk_page_end,
                    content=content,
                    token_estimate=_estimate_tokens(content),
                    section_heading=current_heading,
                )
            )

    return chunks
