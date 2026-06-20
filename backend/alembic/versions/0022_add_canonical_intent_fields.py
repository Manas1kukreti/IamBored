"""add canonical intent persistence fields

Revision ID: 0022_add_canonical_intent_fields
Revises: 0021_callback_nullability
Create Date: 2026-06-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0022_add_canonical_intent_fields"
down_revision = "0021_callback_nullability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column("canonical_intent", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "submissions",
        sa.Column("canonical_intent_schema_version", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "submissions",
        sa.Column("intent_status", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "submissions",
        sa.Column("intent_extractor_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "submissions",
        sa.Column("intent_normalizer_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "submissions",
        sa.Column("intent_grounding_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "submissions",
        sa.Column("intent_created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("submissions", "intent_created_at")
    op.drop_column("submissions", "intent_grounding_version")
    op.drop_column("submissions", "intent_normalizer_version")
    op.drop_column("submissions", "intent_extractor_version")
    op.drop_column("submissions", "intent_status")
    op.drop_column("submissions", "canonical_intent_schema_version")
    op.drop_column("submissions", "canonical_intent")
