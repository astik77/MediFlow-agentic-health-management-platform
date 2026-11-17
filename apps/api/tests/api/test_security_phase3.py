"""
Phase 3 — Security Tests for Document Management.
Verifies SEC-001/002 (cross-patient isolation), SEC-004 (unauthenticated rejection),
SEC-007 (MIME validation), SEC-008 (file signature check), SEC-009 (path traversal),
and SEC-010 (resource exhaustion / upload size limit).
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from mediflow.core.dependencies import SESSION_COOKIE_NAME
from mediflow.modules.auth.models import User
from mediflow.modules.patients.models import PatientProfile

PDF_MAGIC = b"%PDF-1.4 test document content for security tests"
JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 100 + b"fake jpeg content"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50 + b"fake png content"


def _pdf_file(name: str = "report.pdf") -> dict[str, Any]:
    return {"file": (name, io.BytesIO(PDF_MAGIC), "application/pdf")}


# ---------------------------------------------------------------------------
# SEC-004: Unauthenticated access is rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec004_unauthenticated_upload_rejected(
    test_client: AsyncClient,
) -> None:
    """SEC-004: Uploading without a session cookie returns 401."""
    resp = await test_client.post(
        "/api/v1/documents",
        files={"file": ("test.pdf", io.BytesIO(PDF_MAGIC), "application/pdf")},
        data={"title": "Unauth Upload"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sec004_unauthenticated_list_rejected(
    test_client: AsyncClient,
) -> None:
    """SEC-004: Listing documents without a session returns 401."""
    resp = await test_client.get("/api/v1/documents")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sec004_unauthenticated_download_rejected(
    test_client: AsyncClient,
) -> None:
    """SEC-004: Download without a session returns 401."""
    resp = await test_client.get(f"/api/v1/documents/{uuid.uuid4()}/download")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# SEC-007: MIME type validation — unsupported types rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec007_text_file_rejected(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-007: text/plain is not in the allowed MIME list -> 415."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", io.BytesIO(b"plain text"), "text/plain")},
        data={"title": "Plain Text"},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_sec007_executable_rejected(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-007: application/x-msdownload (exe) is rejected -> 415."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={
            "file": (
                "malware.exe",
                io.BytesIO(b"MZ\x90\x00" + b"\x00" * 100),
                "application/x-msdownload",
            )
        },
        data={"title": "Malware"},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_sec007_html_rejected(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-007: text/html is rejected -> 415."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={
            "file": (
                "xss.html",
                io.BytesIO(b"<html><script>alert(1)</script></html>"),
                "text/html",
            )
        },
        data={"title": "XSS Attempt"},
    )
    assert resp.status_code == 415


# ---------------------------------------------------------------------------
# SEC-008: File signature mismatch — declared MIME != actual magic bytes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec008_pdf_declared_but_exe_content_rejected(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-008: Content-Type says PDF but file starts with EXE magic -> 400."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    exe_magic = b"MZ\x90\x00" + b"\x00" * 100
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("disguised.pdf", io.BytesIO(exe_magic), "application/pdf")},
        data={"title": "Disguised EXE"},
    )
    assert resp.status_code == 400
    # Ensure no rejected file was left on disk
    assert list(tmp_path.rglob("*.pdf")) == []


@pytest.mark.asyncio
async def test_sec008_jpeg_declared_but_pdf_content_rejected(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-008: Content-Type says JPEG but file starts with PDF magic -> 400."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("wrong.jpg", io.BytesIO(PDF_MAGIC), "image/jpeg")},
        data={"title": "MIME Mismatch"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sec008_png_declared_but_random_bytes_rejected(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-008: Content-Type says PNG but content has no PNG magic -> 400."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("fake.png", io.BytesIO(b"\x00" * 200), "image/png")},
        data={"title": "Fake PNG"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# SEC-009: Path traversal prevention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec009_path_traversal_in_filename(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    SEC-009: Even if the original filename contains POSIX or Windows path traversal
    segments, stored_filename is UUID-only and file stays inside patient's directory.
    """
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    traversal_name = "..\\..\\etc/passwd"
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": (traversal_name, io.BytesIO(PDF_MAGIC), "application/pdf")},
        data={"title": "Traversal Test"},
    )
    assert resp.status_code == 201
    body = resp.json()
    stored = body["stored_filename"]
    assert "/" not in stored
    assert "\\" not in stored
    assert ".." not in stored
    assert stored.endswith(".pdf")
    assert body["original_filename"] == "passwd"
    assert "file_path" not in body
    expected_path = (tmp_path / body["patient_id"] / stored).resolve()
    assert expected_path.exists()
    assert expected_path.is_relative_to(tmp_path.resolve())


# ---------------------------------------------------------------------------
# SEC-010: Resource exhaustion — oversized & empty files rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sec010_oversized_file_rejected(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-010: File exceeding max_upload_size_mb is rejected with 413 and cleaned up."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    monkeypatch.setattr("mediflow.api.v1.routers.documents._max_bytes", lambda: 10)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("big.pdf", io.BytesIO(PDF_MAGIC), "application/pdf")},
        data={"title": "Too Big"},
    )
    assert resp.status_code == 413
    assert list(tmp_path.rglob("*.pdf")) == []


@pytest.mark.asyncio
async def test_sec010_empty_file_rejected(
    authenticated_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-010: Empty file upload returns 400."""
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)
    resp = await authenticated_client.post(
        "/api/v1/documents",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        data={"title": "Empty File"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# SEC-001/002: Cross-patient isolation — another patient gets 403 Forbidden
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_patient_document_access_forbidden(
    test_client: AsyncClient,
    test_patient: tuple[User, PatientProfile, str],
    second_patient: tuple[User, PatientProfile, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    SEC-001/002: Patient B cannot see, read, download, update, or archive
    Patient A's documents (direct ID operations return 403 Forbidden).
    """
    monkeypatch.setattr("mediflow.api.v1.routers.documents._storage_root", lambda: tmp_path)

    _, _, token_a = test_patient
    _, _, token_b = second_patient

    # Patient A uploads a document
    test_client.cookies.set(SESSION_COOKIE_NAME, token_a)
    r = await test_client.post(
        "/api/v1/documents",
        files=_pdf_file(),
        data={"title": "Patient A Private Doc"},
    )
    assert r.status_code == 201
    doc_id = r.json()["id"]

    # Switch to Patient B
    test_client.cookies.set(SESSION_COOKIE_NAME, token_b)

    # Patient B's list must be empty
    list_b = await test_client.get("/api/v1/documents")
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 0

    # Patient B direct metadata / download / update / archive -> 403 Forbidden
    assert (await test_client.get(f"/api/v1/documents/{doc_id}")).status_code == 403
    assert (await test_client.get(f"/api/v1/documents/{doc_id}/download")).status_code == 403
    assert (
        await test_client.patch(
            f"/api/v1/documents/{doc_id}", json={"title": "Stolen"}
        )
    ).status_code == 403
    assert (await test_client.delete(f"/api/v1/documents/{doc_id}")).status_code == 403
