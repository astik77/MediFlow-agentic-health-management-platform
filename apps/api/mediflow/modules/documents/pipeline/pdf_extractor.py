"""
PDF & Image Page Extractor.
Uses PyMuPDF (fitz) for native digital PDF text extraction & page rasterization,
falling back automatically to the pluggable OcrBackend for scanned PDFs and image uploads.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image, ImageSequence

from mediflow.modules.documents.pipeline.image_preprocessor import preprocess_image_bytes
from mediflow.modules.documents.pipeline.ocr_engine import OcrBackend, get_default_ocr_backend


@dataclass(slots=True)
class ExtractedPage:
    """Extracted text and metadata for a single document page (1-indexed)."""

    page_number: int
    extraction_method: str  # pymupdf_text | rapidocr | hybrid | failed
    raw_text: str
    ocr_confidence: float | None = None
    layout_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractionOutput:
    """Complete extraction result across all processed pages of a document."""

    total_pages: int
    pages_processed: int
    truncated: bool
    pages: list[ExtractedPage]


def _extract_pdf_page_lines(page: pymupdf.Page) -> str:
    """
    Extract native PDF text preserving horizontal table rows by grouping text spans
    that share the same vertical baseline.
    """
    text_dict = page.get_text("dict")
    spans: list[tuple[float, float, float, float, str]] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                txt = str(span.get("text", "")).strip()
                if not txt:
                    continue
                x0, y0, x1, y1 = span["bbox"]
                spans.append((x0, y0, x1, y1, txt))

    if not spans:
        return page.get_text("text").strip()

    spans.sort(key=lambda s: ((s[1] + s[3]) / 2.0, s[0]))
    rows: list[list[tuple[float, float, float, float, str]]] = []
    for sp in spans:
        y_mid = (sp[1] + sp[3]) / 2.0
        sp_h = max(1.0, sp[3] - sp[1])
        placed = False
        for row in rows:
            ref = row[0]
            ref_mid = (ref[1] + ref[3]) / 2.0
            ref_h = max(1.0, ref[3] - ref[1])
            if abs(y_mid - ref_mid) <= max((sp_h + ref_h) * 0.35, 3.0):
                row.append(sp)
                placed = True
                break
        if not placed:
            rows.append([sp])

    rows.sort(key=lambda r: min((s[1] + s[3]) / 2.0 for s in r))
    output_lines: list[str] = []
    for row in rows:
        row.sort(key=lambda s: s[0])
        parts: list[str] = []
        prev_x1: float | None = None
        for x0, y0, x1, y1, txt in row:
            if prev_x1 is not None:
                gap = x0 - prev_x1
                h = max(1.0, y1 - y0)
                sep = "  " if gap > max(h * 0.85, 8.0) else " "
                parts.append(sep + txt)
            else:
                parts.append(txt)
            prev_x1 = x1
        output_lines.append("".join(parts))

    return "\n".join(output_lines).strip()


def extract_document_pages(
    file_path: Path,
    mime_type: str,
    *,
    max_pages: int = 50,
    ocr_dpi: int = 200,
    min_text_chars_per_page: int = 40,
    ocr_backend: OcrBackend | None = None,
) -> ExtractionOutput:
    """
    Extract page-indexed text from a PDF or image file.
    - Digital PDFs use fast, exact PyMuPDF extraction.
    - Scanned PDF pages (below min_text_chars_per_page) are rasterized and OCR'd.
    - Image files (JPEG, PNG, WebP, single/multi-page TIFF) go through preprocessing + OCR.
    """
    backend = ocr_backend or get_default_ocr_backend()
    pages: list[ExtractedPage] = []

    if mime_type == "application/pdf":
        with pymupdf.open(str(file_path)) as pdf_doc:
            total_pages = len(pdf_doc)
            limit = min(total_pages, max_pages)
            truncated = total_pages > max_pages

            for idx in range(limit):
                page_num = idx + 1
                pdf_page = pdf_doc[idx]
                native_text = _extract_pdf_page_lines(pdf_page)

                if len(native_text) >= min_text_chars_per_page:
                    pages.append(
                        ExtractedPage(
                            page_number=page_num,
                            extraction_method="pymupdf_text",
                            raw_text=native_text,
                            ocr_confidence=1.0,
                            layout_metadata={
                                "width_pt": round(float(pdf_page.rect.width), 1),
                                "height_pt": round(float(pdf_page.rect.height), 1),
                            },
                        )
                    )
                else:
                    # Rasterize scanned page and run local OCR
                    pix = pdf_page.get_pixmap(dpi=ocr_dpi)
                    png_bytes = pix.tobytes("png")
                    pre = preprocess_image_bytes(png_bytes)
                    ocr_res = backend.recognize(pre.image_bgr)
                    combined = ocr_res.text.strip() or native_text
                    method = "hybrid" if native_text and ocr_res.text.strip() else backend.name
                    pages.append(
                        ExtractedPage(
                            page_number=page_num,
                            extraction_method=method,
                            raw_text=combined,
                            ocr_confidence=ocr_res.mean_confidence,
                            layout_metadata={
                                "width_px": pre.width,
                                "height_px": pre.height,
                                "dpi": ocr_dpi,
                                "box_count": len(ocr_res.boxes),
                                "preprocess_steps": pre.applied_steps,
                            },
                        )
                    )

        return ExtractionOutput(
            total_pages=total_pages,
            pages_processed=len(pages),
            truncated=truncated,
            pages=pages,
        )

    # Image uploads (JPEG, PNG, WebP, single or multi-frame TIFF)
    raw_bytes = file_path.read_bytes()
    with Image.open(io.BytesIO(raw_bytes)) as img:
        frames = [frame.copy() for frame in ImageSequence.Iterator(img)]

    total_pages = len(frames)
    limit = min(total_pages, max_pages)
    truncated = total_pages > max_pages

    for idx in range(limit):
        page_num = idx + 1
        buf = io.BytesIO()
        frames[idx].convert("RGB").save(buf, format="PNG")
        pre = preprocess_image_bytes(buf.getvalue())
        ocr_res = backend.recognize(pre.image_bgr)
        pages.append(
            ExtractedPage(
                page_number=page_num,
                extraction_method=backend.name,
                raw_text=ocr_res.text.strip(),
                ocr_confidence=ocr_res.mean_confidence,
                layout_metadata={
                    "width_px": pre.width,
                    "height_px": pre.height,
                    "box_count": len(ocr_res.boxes),
                    "preprocess_steps": pre.applied_steps,
                },
            )
        )

    return ExtractionOutput(
        total_pages=total_pages,
        pages_processed=len(pages),
        truncated=truncated,
        pages=pages,
    )
