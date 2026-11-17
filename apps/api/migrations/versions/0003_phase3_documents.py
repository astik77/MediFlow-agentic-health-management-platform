"""
Phase 3: Documents table.
Creates the documents table with all Phase 3 fields.

Revision ID: 0003_phase3_documents
Revises: 0002_phase2_medical_history
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "0003_phase3_documents"
down_revision: str | None = "0002_phase2_medical_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "patient_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploader_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # File identity
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False, unique=True),
        sa.Column("file_path", sa.String(500), nullable=False),
        # File properties
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        # Classification
        sa.Column("document_type", sa.String(50), nullable=False, server_default="other"),
        sa.Column(
            "source_type", sa.String(32), nullable=False, server_default="patient_uploaded"
        ),
        # Status
        sa.Column("upload_status", sa.String(32), nullable=False, server_default="ready"),
        sa.Column(
            "review_status", sa.String(32), nullable=False, server_default="unreviewed"
        ),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column("processing_metadata", sa.JSON, nullable=True),
        # Content metadata
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("document_date", sa.Date, nullable=True),
        sa.Column("page_count", sa.Integer, nullable=True),
        # Lifecycle
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Indexes
    op.create_index("ix_documents_patient_id", "documents", ["patient_id"])
    op.create_index("ix_documents_sha256_hash", "documents", ["sha256_hash"])
    op.create_index(
        "ix_documents_patient_uploaded",
        "documents",
        ["patient_id", sa.text("uploaded_at DESC")],
    )
    op.create_index(
        "ix_documents_patient_type",
        "documents",
        ["patient_id", "document_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_patient_type", table_name="documents")
    op.drop_index("ix_documents_patient_uploaded", table_name="documents")
    op.drop_index("ix_documents_sha256_hash", table_name="documents")
    op.drop_index("ix_documents_patient_id", table_name="documents")
    op.drop_table("documents")
