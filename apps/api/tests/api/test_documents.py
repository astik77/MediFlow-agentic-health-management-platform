"""
Phase 3 — Document Management API Tests.
Covers upload, list, metadata retrieval, download, metadata update, and soft-archive.
"""
from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PDF_MAGIC = b"%PDF-1.4 test document content for MediFlow Phase 3 tests"
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"fake jpeg content for testing"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50 + b"fake png content for testing"
WEBP_MAGIC = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 50


def _pdf_file(name: str = "report.pdf") -> dict[str, Any]:
    return {
        "file": (name, io.BytesIO(PDF_MAGIC), "application/pdf"),
    }


def _jpeg_file(name: str = "scan.jpg") -> dict[str, Any]:
    return {
        "file": (name, io.BytesIO(JPEG_MAGIC), "image/jpeg"),
    }


def _png_file(name: str = "xray.png") -> dict[str, Any]:
    return {
        "file": (name, io.BytesIO(PNG_MAGIC), "image/png"),
    }


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_pdf(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-001: Valid PDF upload succeeds and returns metadata."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={"document_type": "lab_report", "title": "Blood Test Report"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["mime_type"] == "application/pdf"
    assert body["document_type"] == "lab_report"
    assert body["title"] == "Blood Test Report"
    assert body["upload_status"] == "ready"
    assert body["is_archived"] is False
    assert "file_path" not in body  # SEC: never expose internal path
    assert len(body["sha256_hash"]) == 64


@pytest.mark.asyncio
async def test_upload_jpeg(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-002: Valid JPEG upload succeeds."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files=_jpeg_file(),
        data={"document_type": "imaging", "title": "X-Ray"},
    )
    assert resp.status_code == 201
    assert resp.json()["mime_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_upload_png(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-003: Valid PNG upload succeeds."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files=_png_file(),
        data={"document_type": "clinical_note", "title": "Clinical Scan"},
    )
    assert resp.status_code == 201
    assert resp.json()["mime_type"] == "image/png"


@pytest.mark.asyncio
async def test_upload_default_title_from_filename(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-004: When title is omitted, original filename is used as title."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("my_lab.pdf", io.BytesIO(PDF_MAGIC), "application/pdf")},
        data={},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "my_lab.pdf"


@pytest.mark.asyncio
async def test_upload_sha256_integrity(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-005: SHA-256 hash in response matches actual file content."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    content = PDF_MAGIC
    expected_hash = hashlib.sha256(content).hexdigest()
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("hash_test.pdf", io.BytesIO(content), "application/pdf")},
        data={"title": "Hash Test"},
    )
    assert resp.status_code == 201
    assert resp.json()["sha256_hash"] == expected_hash


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_documents_empty(
    authenticated_client: AsyncClient,
) -> None:
    """DOC-006: Empty list returned when no documents uploaded."""
    resp = await authenticated_client.get("/api/v1/documents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_list_documents_after_upload(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-007: Uploaded documents appear in list."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    for i in range(3):
        await authenticated_client.post(
            "/api/v1/documents",
            files={"file": (f"doc{i}.pdf", io.BytesIO(PDF_MAGIC), "application/pdf")},
            data={"title": f"Doc {i}"},
        )
    resp = await authenticated_client.get("/api/v1/documents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_list_filter_by_document_type(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-008: document_type filter works."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={"document_type": "lab_report", "title": "Lab"},
    )
    await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={"document_type": "prescription", "title": "Rx"},
    )
    resp = await authenticated_client.get("/api/v1/documents?document_type=lab_report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["document_type"] == "lab_report"


@pytest.mark.asyncio
async def test_list_excludes_archived_by_default(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-009: Archived documents are excluded from default list."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    r = await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file("to_archive.pdf"),
        data={"title": "To Archive"},
    )
    doc_id = r.json()["id"]
    await authenticated_client.delete(f"/api/v1/documents/{doc_id}")
    resp = await authenticated_client.get("/api/v1/documents")
    assert resp.json()["total"] == 0

    resp_incl = await authenticated_client.get("/api/v1/documents?include_archived=true")
    assert resp_incl.json()["total"] == 1


# ---------------------------------------------------------------------------
# Get metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_document_metadata(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-010: Get specific document by ID returns full metadata."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    r = await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={"title": "My Report", "document_type": "lab_report"},
    )
    doc_id = r.json()["id"]
    resp = await authenticated_client.get(f"/api/v1/documents/{doc_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == doc_id
    assert body["title"] == "My Report"
    assert "file_path" not in body


@pytest.mark.asyncio
async def test_get_nonexistent_document_returns_404(
    authenticated_client: AsyncClient,
) -> None:
    """DOC-011: 404 for unknown document ID."""
    resp = await authenticated_client.get(f"/api/v1/documents/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_document(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-012: Download returns the original file content."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    content = PDF_MAGIC
    r = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("report.pdf", io.BytesIO(content), "application/pdf")},
        data={"title": "Download Test"},
    )
    doc_id = r.json()["id"]
    dl = await authenticated_client.get(f"/api/v1/documents/{doc_id}/download")
    assert dl.status_code == 200
    assert dl.content == content
    assert "attachment" in dl.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_download_archived_returns_410(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-013: Download of archived document returns 410 Gone."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    r = await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={"title": "Archive Then Download"},
    )
    doc_id = r.json()["id"]
    await authenticated_client.delete(f"/api/v1/documents/{doc_id}")
    dl = await authenticated_client.get(f"/api/v1/documents/{doc_id}/download")
    assert dl.status_code == 410


# ---------------------------------------------------------------------------
# Update metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_document_metadata(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-014: Partial metadata update succeeds."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    r = await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={"title": "Original Title", "document_type": "other"},
    )
    doc_id = r.json()["id"]
    resp = await authenticated_client.patch(
        f"/api/v1/documents/{doc_id}",
        json={
            "title": "Updated Title",
            "document_type": "prescription",
            "review_status": "reviewed",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Updated Title"
    assert body["document_type"] == "prescription"
    assert body["review_status"] == "reviewed"


@pytest.mark.asyncio
async def test_update_archived_document_returns_409(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-015: Updating an archived document returns 409 Conflict."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    r = await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={"title": "To Archive"},
    )
    doc_id = r.json()["id"]
    await authenticated_client.delete(f"/api/v1/documents/{doc_id}")
    resp = await authenticated_client.patch(
        f"/api/v1/documents/{doc_id}",
        json={"title": "Should Fail"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Soft-archive (DELETE)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archive_document(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-016: Archive sets is_archived=True, removes file from disk, and keeps metadata."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    r = await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={"title": "Delete Me"},
    )
    doc_data = r.json()
    doc_id = doc_data["id"]
    stored_file = tmp_path / doc_data["patient_id"] / doc_data["stored_filename"]
    assert stored_file.exists()

    resp = await authenticated_client.delete(f"/api/v1/documents/{doc_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_archived"] is True
    assert body["upload_status"] == "archived"
    assert not stored_file.exists()


@pytest.mark.asyncio
async def test_archive_already_archived_returns_409(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-017: Double-archive returns 409 Conflict."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    r = await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={"title": "Double Archive"},
    )
    doc_id = r.json()["id"]
    await authenticated_client.delete(f"/api/v1/documents/{doc_id}")
    resp = await authenticated_client.delete(f"/api/v1/documents/{doc_id}")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Timeline events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_creates_timeline_event(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-018: Upload creates a 'document' timeline event linked to the document."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    up = await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={
            "title": "Timeline Test",
            "document_type": "prescription",
            "document_date": "2026-05-10",
        },
    )
    assert up.status_code == 201
    doc_id = up.json()["id"]

    resp = await authenticated_client.get("/api/v1/timeline?category=document")
    assert resp.status_code == 200
    events = resp.json()["items"]
    assert len(events) == 1
    assert events[0]["event_category"] == "document"
    assert events[0]["related_entity_type"] == "document"
    assert events[0]["related_entity_id"] == doc_id
    assert events[0]["event_occurred_at"].startswith("2026-05-10")


@pytest.mark.asyncio
async def test_list_search_and_date_filter(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-020: Search query and clinical date range filters work accurately."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file("cbc.pdf"),
        data={
            "title": "Complete Blood Count",
            "document_type": "lab_report",
            "document_date": "2026-01-15",
        },
    )
    await authenticated_client.post(
        "/api/v1/documents",
        files=_pdf_file("mri.pdf"),
        data={
            "title": "Knee MRI Scan",
            "document_type": "imaging",
            "document_date": "2026-06-20",
        },
    )

    resp_q = await authenticated_client.get("/api/v1/documents?q=Blood")
    assert resp_q.status_code == 200
    assert resp_q.json()["total"] == 1
    assert resp_q.json()["items"][0]["title"] == "Complete Blood Count"

    resp_date = await authenticated_client.get(
        "/api/v1/documents?start_date=2026-06-01&end_date=2026-06-30"
    )
    assert resp_date.status_code == 200
    assert resp_date.json()["total"] == 1
    assert resp_date.json()["items"][0]["title"] == "Knee MRI Scan"


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_pagination(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOC-019: Pagination metadata is correct."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    for i in range(5):
        await authenticated_client.post(
            "/api/v1/documents",
            files={"file": (f"p{i}.pdf", io.BytesIO(PDF_MAGIC), "application/pdf")},
            data={"title": f"Page Doc {i}"},
        )
    resp = await authenticated_client.get("/api/v1/documents?page=1&page_size=2")
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["has_next"] is True
    assert body["page"] == 1

    resp2 = await authenticated_client.get("/api/v1/documents?page=3&page_size=2")
    body2 = resp2.json()
    assert len(body2["items"]) == 1
    assert body2["has_next"] is False
