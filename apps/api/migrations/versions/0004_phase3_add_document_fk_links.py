"""
Phase 3: Add FK from health_record source_document_id columns -> documents.id.

Adds SET NULL foreign keys so health records can reference documents without
creating hard dependencies — if a document is archived, source_document_id is
set to NULL rather than cascading the delete.

Revision ID: 0004_phase3_add_document_fk_links
Revises: 0003_phase3_documents
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_phase3_add_document_fk_links"
down_revision: str | None = "0003_phase3_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables and their source_document_id columns that reference documents
_TABLES = [
    "patient_conditions",
    "patient_allergies",
    "patient_symptoms",
    "health_observations",
]


def upgrade() -> None:
    for table in _TABLES:
        op.create_foreign_key(
            constraint_name=f"fk_{table}_source_document_id",
            source_table=table,
            referent_table="documents",
            local_cols=["source_document_id"],
            remote_cols=["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_constraint(
            constraint_name=f"fk_{table}_source_document_id",
            table_name=table,
            type_="foreignkey",
        )
