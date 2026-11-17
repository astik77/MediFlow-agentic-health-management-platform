"""
Phase 4: Document Intelligence tables.
Creates document_pages, document_chunks, and document_processing_jobs.

Revision ID: 0005_phase4_document_intelligence
Revises: 0004_phase3_add_document_fk_links
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_phase4_document_intelligence"
down_revision: str | None = "0004_phase3_add_document_fk_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_pages",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_number", sa.Integer, nullable=False),
        sa.Column("extraction_method", sa.String(32), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False, server_default=""),
        sa.Column("ocr_confidence", sa.Float, nullable=True),
        sa.Column("char_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("layout_metadata", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("document_id", "page_number", name="uq_document_pages_doc_page"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])
    op.create_index("ix_document_pages_patient_id", "document_pages", ["patient_id"])
    op.create_index(
        "ix_document_pages_patient_doc",
        "document_pages",
        ["patient_id", "document_id"],
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("page_start", sa.Integer, nullable=False),
        sa.Column("page_end", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("token_estimate", sa.Integer, nullable=False, server_default="0"),
        sa.Column("section_heading", sa.String(255), nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_doc_idx"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_patient_id", "document_chunks", ["patient_id"])
    op.create_index(
        "ix_document_chunks_patient_doc",
        "document_chunks",
        ["patient_id", "document_id"],
    )

    op.create_table(
        "document_processing_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("pipeline_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metrics_json", sa.JSON, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
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
    op.create_index(
        "ix_document_processing_jobs_document_id",
        "document_processing_jobs",
        ["document_id"],
    )
    op.create_index(
        "ix_document_processing_jobs_patient_id",
        "document_processing_jobs",
        ["patient_id"],
    )
    op.create_index(
        "ix_document_processing_jobs_status",
        "document_processing_jobs",
        ["status"],
    )
    op.create_index(
        "ix_document_jobs_doc_created",
        "document_processing_jobs",
        ["document_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_document_jobs_doc_created", table_name="document_processing_jobs")
    op.drop_index("ix_document_processing_jobs_status", table_name="document_processing_jobs")
    op.drop_index("ix_document_processing_jobs_patient_id", table_name="document_processing_jobs")
    op.drop_index("ix_document_processing_jobs_document_id", table_name="document_processing_jobs")
    op.drop_table("document_processing_jobs")

    op.drop_index("ix_document_chunks_patient_doc", table_name="document_chunks")
    op.drop_index("ix_document_chunks_patient_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_document_pages_patient_doc", table_name="document_pages")
    op.drop_index("ix_document_pages_patient_id", table_name="document_pages")
    op.drop_index("ix_document_pages_document_id", table_name="document_pages")
    op.drop_table("document_pages")
