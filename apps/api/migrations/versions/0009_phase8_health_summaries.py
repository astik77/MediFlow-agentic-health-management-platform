"""
Phase 8: Longitudinal Health Summaries table.
Creates health_summaries strictly scoped by patient_id (SEC-001/SEC-002)
with composite index on (patient_id, created_at DESC).

Revision ID: 0009_phase8_health_summaries
Revises: 0008_phase7_rag_embeddings
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_phase8_health_summaries"
down_revision: str | None = "0008_phase7_rag_embeddings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "health_summaries",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "patient_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("patient_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("window_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("headline", sa.String(255), nullable=False),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("highlights_json", sa.JSON, nullable=False),
        sa.Column("notable_trends_json", sa.JSON, nullable=False),
        sa.Column("questions_for_doctor_json", sa.JSON, nullable=False),
        sa.Column("metrics_snapshot_json", sa.JSON, nullable=False),
        sa.Column(
            "generation_mode",
            sa.String(32),
            nullable=False,
            server_default="deterministic_fallback",
        ),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("prompt_version", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_health_summaries_patient_id", "health_summaries", ["patient_id"])
    op.create_index("ix_health_summaries_created_at", "health_summaries", ["created_at"])
    op.create_index(
        "ix_health_summaries_patient_created",
        "health_summaries",
        ["patient_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_health_summaries_patient_created", table_name="health_summaries")
    op.drop_index("ix_health_summaries_created_at", table_name="health_summaries")
    op.drop_index("ix_health_summaries_patient_id", table_name="health_summaries")
    op.drop_table("health_summaries")
