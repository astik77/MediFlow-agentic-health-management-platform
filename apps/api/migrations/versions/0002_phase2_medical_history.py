"""Phase 2: medical history foundation and timeline

Revision ID: 0002_phase2_medical_history
Revises: 0001_phase1_auth_patients
Create Date: 2026-11-18 00:42:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_phase2_medical_history"
down_revision: str | None = "0001_phase1_auth_patients"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patient_conditions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("patient_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("resolved_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "source_type", sa.String(length=32), nullable=False, server_default="patient_reported"
        ),
        sa.Column(
            "review_status", sa.String(length=32), nullable=False, server_default="confirmed"
        ),
        sa.Column("source_document_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patient_profiles.id"],
            name=op.f("fk_patient_conditions_patient_id_patient_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patient_conditions")),
    )
    op.create_index(
        op.f("ix_patient_conditions_patient_id"), "patient_conditions", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_patient_conditions_is_archived"),
        "patient_conditions",
        ["is_archived"],
        unique=False,
    )

    op.create_table(
        "patient_allergies",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("patient_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("allergen", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("reaction", sa.String(length=500), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="moderate"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "source_type", sa.String(length=32), nullable=False, server_default="patient_reported"
        ),
        sa.Column(
            "review_status", sa.String(length=32), nullable=False, server_default="confirmed"
        ),
        sa.Column("source_document_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patient_profiles.id"],
            name=op.f("fk_patient_allergies_patient_id_patient_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patient_allergies")),
    )
    op.create_index(
        op.f("ix_patient_allergies_patient_id"), "patient_allergies", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_patient_allergies_is_archived"), "patient_allergies", ["is_archived"], unique=False
    )

    op.create_table(
        "patient_symptoms",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("patient_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="moderate"),
        sa.Column("frequency", sa.String(length=100), nullable=True),
        sa.Column("body_location", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ongoing"),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "source_type", sa.String(length=32), nullable=False, server_default="patient_reported"
        ),
        sa.Column(
            "review_status", sa.String(length=32), nullable=False, server_default="confirmed"
        ),
        sa.Column("source_document_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patient_profiles.id"],
            name=op.f("fk_patient_symptoms_patient_id_patient_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patient_symptoms")),
    )
    op.create_index(
        op.f("ix_patient_symptoms_patient_id"), "patient_symptoms", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_patient_symptoms_started_at"), "patient_symptoms", ["started_at"], unique=False
    )
    op.create_index(
        op.f("ix_patient_symptoms_is_archived"), "patient_symptoms", ["is_archived"], unique=False
    )

    op.create_table(
        "health_observations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("patient_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "observation_type", sa.String(length=40), nullable=False, server_default="vital_sign"
        ),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("value_raw", sa.String(length=255), nullable=False),
        sa.Column("unit_raw", sa.String(length=64), nullable=True),
        sa.Column("value_numeric", sa.Float(), nullable=True),
        sa.Column("value_normalized", sa.Float(), nullable=True),
        sa.Column("unit_normalized", sa.String(length=64), nullable=True),
        sa.Column("reference_range_text", sa.String(length=255), nullable=True),
        sa.Column("abnormality_flag", sa.String(length=32), nullable=True),
        sa.Column(
            "observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "source_type", sa.String(length=32), nullable=False, server_default="patient_reported"
        ),
        sa.Column(
            "review_status", sa.String(length=32), nullable=False, server_default="confirmed"
        ),
        sa.Column("source_document_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("extraction_method", sa.String(length=64), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=True),
        sa.Column("provenance_metadata", sa.JSON(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patient_profiles.id"],
            name=op.f("fk_health_observations_patient_id_patient_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_health_observations")),
    )
    op.create_index(
        op.f("ix_health_observations_patient_id"),
        "health_observations",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_health_observations_display_name"),
        "health_observations",
        ["display_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_health_observations_observed_at"),
        "health_observations",
        ["observed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_health_observations_review_status"),
        "health_observations",
        ["review_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_health_observations_is_archived"),
        "health_observations",
        ["is_archived"],
        unique=False,
    )
    op.create_index(
        "ix_health_observations_patient_observed",
        "health_observations",
        ["patient_id", sa.text("observed_at DESC")],
        unique=False,
    )

    op.create_table(
        "health_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("patient_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("event_category", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "event_occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "source_type", sa.String(length=32), nullable=False, server_default="patient_reported"
        ),
        sa.Column(
            "review_status", sa.String(length=32), nullable=False, server_default="confirmed"
        ),
        sa.Column("related_entity_type", sa.String(length=32), nullable=True),
        sa.Column("related_entity_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patient_profiles.id"],
            name=op.f("fk_health_events_patient_id_patient_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_health_events")),
    )
    op.create_index(
        op.f("ix_health_events_patient_id"), "health_events", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_health_events_event_category"), "health_events", ["event_category"], unique=False
    )
    op.create_index(
        op.f("ix_health_events_event_occurred_at"),
        "health_events",
        ["event_occurred_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_health_events_related_entity_id"),
        "health_events",
        ["related_entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_health_events_patient_occurred",
        "health_events",
        ["patient_id", sa.text("event_occurred_at DESC")],
        unique=False,
    )

    op.create_table(
        "record_revisions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("patient_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("previous_data", sa.JSON(), nullable=True),
        sa.Column("new_data", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("changed_by_user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patient_profiles.id"],
            name=op.f("fk_record_revisions_patient_id_patient_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["users.id"],
            name=op.f("fk_record_revisions_changed_by_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_record_revisions")),
    )
    op.create_index(
        op.f("ix_record_revisions_patient_id"), "record_revisions", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_record_revisions_entity_id"), "record_revisions", ["entity_id"], unique=False
    )
    op.create_index(
        "ix_record_revisions_entity_lookup",
        "record_revisions",
        ["patient_id", "entity_type", "entity_id", "revision_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_record_revisions_entity_lookup", table_name="record_revisions")
    op.drop_index(op.f("ix_record_revisions_entity_id"), table_name="record_revisions")
    op.drop_index(op.f("ix_record_revisions_patient_id"), table_name="record_revisions")
    op.drop_table("record_revisions")

    op.drop_index("ix_health_events_patient_occurred", table_name="health_events")
    op.drop_index(op.f("ix_health_events_related_entity_id"), table_name="health_events")
    op.drop_index(op.f("ix_health_events_event_occurred_at"), table_name="health_events")
    op.drop_index(op.f("ix_health_events_event_category"), table_name="health_events")
    op.drop_index(op.f("ix_health_events_patient_id"), table_name="health_events")
    op.drop_table("health_events")

    op.drop_index("ix_health_observations_patient_observed", table_name="health_observations")
    op.drop_index(op.f("ix_health_observations_is_archived"), table_name="health_observations")
    op.drop_index(op.f("ix_health_observations_review_status"), table_name="health_observations")
    op.drop_index(op.f("ix_health_observations_observed_at"), table_name="health_observations")
    op.drop_index(op.f("ix_health_observations_display_name"), table_name="health_observations")
    op.drop_index(op.f("ix_health_observations_patient_id"), table_name="health_observations")
    op.drop_table("health_observations")

    op.drop_index(op.f("ix_patient_symptoms_is_archived"), table_name="patient_symptoms")
    op.drop_index(op.f("ix_patient_symptoms_started_at"), table_name="patient_symptoms")
    op.drop_index(op.f("ix_patient_symptoms_patient_id"), table_name="patient_symptoms")
    op.drop_table("patient_symptoms")

    op.drop_index(op.f("ix_patient_allergies_is_archived"), table_name="patient_allergies")
    op.drop_index(op.f("ix_patient_allergies_patient_id"), table_name="patient_allergies")
    op.drop_table("patient_allergies")

    op.drop_index(op.f("ix_patient_conditions_is_archived"), table_name="patient_conditions")
    op.drop_index(op.f("ix_patient_conditions_patient_id"), table_name="patient_conditions")
    op.drop_table("patient_conditions")
