"""
Phase 5: Local AI Infrastructure tables.
Creates ai_invocation_logs for anonymized AI observability and governance auditing.

Revision ID: 0006_phase5_ai_infrastructure
Revises: 0005_phase4_document_intelligence
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_phase5_ai_infrastructure"
down_revision: str | None = "0005_phase4_document_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_invocation_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "patient_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("prompt_id", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.Column("task_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("schema_valid", sa.Boolean, nullable=True),
        sa.Column("is_synthetic", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_ai_invocation_logs_patient_id", "ai_invocation_logs", ["patient_id"])
    op.create_index("ix_ai_invocation_logs_status", "ai_invocation_logs", ["status"])
    op.create_index("ix_ai_invocation_logs_created_at", "ai_invocation_logs", ["created_at"])
    op.create_index(
        "ix_ai_logs_patient_created",
        "ai_invocation_logs",
        ["patient_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_logs_patient_created", table_name="ai_invocation_logs")
    op.drop_index("ix_ai_invocation_logs_created_at", table_name="ai_invocation_logs")
    op.drop_index("ix_ai_invocation_logs_status", table_name="ai_invocation_logs")
    op.drop_index("ix_ai_invocation_logs_patient_id", table_name="ai_invocation_logs")
    op.drop_table("ai_invocation_logs")
