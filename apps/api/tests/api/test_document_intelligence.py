"""
Phase 4 — Document Intelligence & Candidate Review API Integration Tests.
Covers digital PDF extraction, scanned image OCR (RapidOCR), candidate observation
extraction, pending review queue, confirm / edit_confirm / reject workflows with
immutable RecordRevision history, and forced re-processing preserving confirmed facts.
"""

from __future__ import annotations

import io
from pathlib import Path

import pymupdf
import pytest
from httpx import AsyncClient
from PIL import Image, ImageDraw, ImageFont


def _build_lab_pdf_bytes(lines: list[str]) -> bytes:
    """Create a real multi-line digital PDF in memory via PyMuPDF."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    y = 55
    for line in lines:
        page.insert_text((45, y), line, fontsize=11, fontname="helv")
        y += 20
    raw = doc.tobytes()
    doc.close()
    return raw


def _build_scanned_lab_png_bytes(lines: list[str]) -> bytes:
    """Create a synthetic scanned lab report PNG image for real RapidOCR integration testing."""
    img = Image.new("RGB", (1100, 80 + len(lines) * 46), (250, 250, 250))
    draw = ImageDraw.Draw(img)
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    for candidate_font in ("C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf"):
        if Path(candidate_font).exists():
            font = ImageFont.truetype(candidate_font, 24)
            break
    else:
        font = ImageFont.load_default()
    y = 35
    for line in lines:
        draw.text((40, y), line, fill=(20, 20, 20), font=font)
        y += 44
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_process_digital_pdf_and_review_candidates_lifecycle(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    INT-P4-001: End-to-end digital PDF upload -> process -> inspect extraction ->
    pending candidate queue -> confirm, edit_confirm, reject -> document auto-reviewed.
    """
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)

    pdf_bytes = _build_lab_pdf_bytes(
        [
            "DIAGNOSTIC LABORATORY REPORT",
            "Complete Blood Count & Glucose",
            "Report Date: 15/10/2026",
            "Test Name   Result   Unit   Reference Range",
            "Hemoglobin   11.4   g/dL   12.0 - 16.0",
            "Fasting Blood Glucose   118   mg/dL   70 - 100",
            "Platelets   250   10^3/uL   150 - 450",
        ]
    )

    up = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("cbc_oct.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"document_type": "other", "title": "October Blood Panel"},
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    # Process document
    proc = await authenticated_client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc.status_code == 200
    job = proc.json()
    assert job["status"] == "completed"
    assert job["metrics_json"]["pages_processed"] == 1
    assert job["metrics_json"]["candidates_extracted"] == 3

    # Inspect extraction payload
    ext = await authenticated_client.get(f"/api/v1/documents/{doc_id}/extraction")
    assert ext.status_code == 200
    body = ext.json()
    assert body["document"]["page_count"] == 1
    assert body["document"]["document_type"] == "lab_report"  # Auto-classified from 'other'
    assert body["document"]["document_date"] == "2026-10-15"  # Extracted clinical date
    assert body["classification"]["predicted_type"] == "lab_report"
    assert body["security_flags"] == []
    assert len(body["pages"]) == 1
    assert body["pages"][0]["extraction_method"] == "pymupdf_text"
    assert body["chunks_count"] >= 1

    # All extracted observations MUST be strictly candidate (never auto-confirmed)
    observations = body["observations"]
    assert len(observations) == 3
    for obs in observations:
        assert obs["review_status"] == "candidate"
        assert obs["source_type"] == "document_extracted"
        assert obs["source_document_id"] == doc_id
        assert obs["source_page"] == 1

    # Verify global pending candidates queue endpoint
    queue_res = await authenticated_client.get("/api/v1/health-records/candidates")
    assert queue_res.status_code == 200
    assert len(queue_res.json()) == 3

    by_name = {o["display_name"]: o for o in observations}

    # 1) Confirm Hemoglobin
    hb_id = by_name["Hemoglobin"]["id"]
    c1 = await authenticated_client.post(
        f"/api/v1/documents/{doc_id}/candidates/{hb_id}/review",
        json={"action": "confirm"},
    )
    assert c1.status_code == 200
    assert c1.json()["review_status"] == "confirmed"
    assert c1.json()["source_type"] == "patient_confirmed"
    assert c1.json()["abnormality_flag"] == "low"

    # Double review on already confirmed candidate -> 409 Conflict
    dup = await authenticated_client.post(
        f"/api/v1/documents/{doc_id}/candidates/{hb_id}/review",
        json={"action": "confirm"},
    )
    assert dup.status_code == 409

    # 2) Edit & confirm Fasting Blood Glucose (correct value 118 -> 116)
    glu_id = by_name["Fasting Blood Glucose"]["id"]
    c2 = await authenticated_client.post(
        f"/api/v1/documents/{doc_id}/candidates/{glu_id}/review",
        json={
            "action": "edit_confirm",
            "value_raw": "116",
            "reason": "Verified original lab printout",
        },
    )
    assert c2.status_code == 200
    assert c2.json()["value_raw"] == "116"
    assert c2.json()["value_numeric"] == 116.0
    assert c2.json()["review_status"] == "confirmed"

    # Verify immutable RecordRevision trail recorded the edit_confirm
    hist = await authenticated_client.get(f"/api/v1/health-records/observations/{glu_id}/history")
    assert hist.status_code == 200
    assert len(hist.json()) == 1
    assert hist.json()[0]["previous_data"]["value_raw"] == "118"
    assert hist.json()[0]["new_data"]["value_raw"] == "116"

    # 3) Reject Platelets
    plt_id = by_name["Platelets"]["id"]
    c3 = await authenticated_client.post(
        f"/api/v1/documents/{doc_id}/candidates/{plt_id}/review",
        json={"action": "reject", "reason": "Duplicate entry"},
    )
    assert c3.status_code == 200
    assert c3.json()["review_status"] == "rejected"
    assert c3.json()["is_archived"] is True

    # Document automatically transitions to reviewed once all candidates are finalized
    doc_after = await authenticated_client.get(f"/api/v1/documents/{doc_id}")
    assert doc_after.json()["review_status"] == "reviewed"

    # Pending queue should now be empty
    queue_after = await authenticated_client.get("/api/v1/health-records/candidates")
    assert queue_after.json() == []


@pytest.mark.asyncio
async def test_process_scanned_image_via_rapidocr(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    INT-P4-002: Scanned PNG lab report runs through Pillow/OpenCV + RapidOCR
    and produces accurate candidate observations.
    """
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)

    png_bytes = _build_scanned_lab_png_bytes(
        [
            "SYNTHETIC LABORATORY REPORT",
            "Report Date: 2026-11-04",
            "Hemoglobin: 14.1 g/dL (12.0 - 16.0)",
            "TSH: 2.8 mIU/L (0.4 - 4.0)",
        ]
    )

    up = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("scan_lab.png", io.BytesIO(png_bytes), "image/png")},
        data={"document_type": "lab_report", "title": "Scanned Lab Photo"},
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    proc = await authenticated_client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc.status_code == 200
    assert proc.json()["status"] == "completed"

    ext = await authenticated_client.get(f"/api/v1/documents/{doc_id}/extraction")
    body = ext.json()
    assert len(body["pages"]) == 1
    assert body["pages"][0]["extraction_method"] == "rapidocr"
    assert body["pages"][0]["ocr_confidence"] is not None
    assert body["pages"][0]["ocr_confidence"] >= 0.85

    names = {o["display_name"].lower(): o for o in body["observations"]}
    assert "hemoglobin" in names
    assert names["hemoglobin"]["value_raw"] == "14.1"
    assert "tsh" in names
    assert names["tsh"]["value_raw"] == "2.8"


@pytest.mark.asyncio
async def test_force_reprocess_preserves_confirmed_observations(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    INT-P4-003: Re-processing with force=true refreshes pages/chunks and unconfirmed
    candidates without deleting or altering patient-confirmed observations.
    """
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)

    pdf_bytes = _build_lab_pdf_bytes(
        [
            "LABORATORY REPORT",
            "Report Date: 12/11/2026",
            "Hemoglobin   13.6   g/dL   12.0 - 16.0",
        ]
    )
    up = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("reproc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"title": "Reprocess Test"},
    )
    doc_id = up.json()["id"]

    await authenticated_client.post(f"/api/v1/documents/{doc_id}/process")
    ext1 = (await authenticated_client.get(f"/api/v1/documents/{doc_id}/extraction")).json()
    obs_id = ext1["observations"][0]["id"]

    # Patient confirms observation
    await authenticated_client.post(
        f"/api/v1/documents/{doc_id}/candidates/{obs_id}/review",
        json={"action": "confirm"},
    )

    # Force reprocess
    proc2 = await authenticated_client.post(f"/api/v1/documents/{doc_id}/process?force=true")
    assert proc2.status_code == 200
    assert proc2.json()["attempt_count"] == 2

    # Confirmed observation still exists & remains confirmed
    obs_res = await authenticated_client.get(f"/api/v1/health-records/observations/{obs_id}")
    assert obs_res.status_code == 200
    assert obs_res.json()["review_status"] == "confirmed"
