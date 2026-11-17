"""
Phase 7: Patient-Specific RAG Embeddings table.
Creates document_embeddings strictly scoped by patient_id (SEC-003) with
CASCADE deletion linked to document_chunks and documents (SEC-016).

Revision ID: 0008_phase7_rag_embeddings
Revises: 0007_phase6_conversations
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_phase7_rag_embeddings"
down_revision: str | None = "0007_phase6_conversations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_embeddings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "chunk_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("document_chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
        sa.Column("embedding_model", sa.String(100), nullable=False),
        sa.Column("dimensions", sa.Integer, nullable=False),
        sa.Column("embedding_vector", sa.JSON, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("chunk_id", name="uq_document_embeddings_chunk_id"),
    )
    op.create_index("ix_document_embeddings_chunk_id", "document_embeddings", ["chunk_id"])
    op.create_index("ix_document_embeddings_document_id", "document_embeddings", ["document_id"])
    op.create_index("ix_document_embeddings_patient_id", "document_embeddings", ["patient_id"])
    op.create_index(
        "ix_doc_embeddings_patient_doc",
        "document_embeddings",
        ["patient_id", "document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_doc_embeddings_patient_doc", table_name="document_embeddings")
    op.drop_index("ix_document_embeddings_patient_id", table_name="document_embeddings")
    op.drop_index("ix_document_embeddings_document_id", table_name="document_embeddings")
    op.drop_index("ix_document_embeddings_chunk_id", table_name="document_embeddings")
    op.drop_table("document_embeddings")
