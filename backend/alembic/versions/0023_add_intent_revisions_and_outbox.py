"""Add immutable canonical intent revision and outbox tables.

Revision ID: 0023_add_intent_outbox
Revises: 0022_add_canonical_intent_fields
Create Date: 2026-06-20 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0023_add_intent_outbox"
down_revision = "0022_add_canonical_intent_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("intent_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("submissions", sa.Column("intent_revision", sa.Integer(), nullable=True))
    op.add_column("submissions", sa.Column("intent_hash", sa.String(length=64), nullable=True))
    op.add_column("submissions", sa.Column("parent_intent_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("submissions", sa.Column("grounded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("submissions", sa.Column("capability_version", sa.String(length=32), nullable=True))

    op.create_table(
        "canonical_intent_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("intent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intent_revision", sa.Integer(), nullable=False),
        sa.Column("intent_hash", sa.String(length=64), nullable=False),
        sa.Column("parent_intent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("canonical_intent", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("original_instruction", sa.Text(), nullable=False, server_default=""),
        sa.Column("grounded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("capability_version", sa.String(length=32), nullable=True),
        sa.Column("extractor_version", sa.String(length=32), nullable=True),
        sa.Column("normalizer_version", sa.String(length=32), nullable=True),
        sa.Column("grounding_version", sa.String(length=32), nullable=True),
        sa.Column("compiler_version", sa.String(length=32), nullable=True),
        sa.Column("execution_plan_id", sa.String(length=64), nullable=True),
        sa.Column("execution_plan_hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("intent_id", "intent_revision", name="uq_canonical_intent_revision"),
    )

    op.create_table(
        "intent_dispatch_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("intent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intent_revision", sa.Integer(), nullable=False),
        sa.Column("intent_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.UniqueConstraint("submission_id", "intent_hash", name="uq_intent_dispatch_outbox_submission_hash"),
    )


def downgrade() -> None:
    op.drop_table("intent_dispatch_outbox")
    op.drop_table("canonical_intent_revisions")
    op.drop_column("submissions", "capability_version")
    op.drop_column("submissions", "grounded_at")
    op.drop_column("submissions", "parent_intent_id")
    op.drop_column("submissions", "intent_hash")
    op.drop_column("submissions", "intent_revision")
    op.drop_column("submissions", "intent_id")
