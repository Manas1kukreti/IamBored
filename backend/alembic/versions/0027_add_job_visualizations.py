"""Add job_visualizations table for chart visualization persistence.

Revision ID: 0027_add_job_visualizations
Revises: 0026_add_clarify_status
Create Date: 2026-06-23 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0027_add_job_visualizations"
down_revision = "0026_add_clarify_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_visualizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("submissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("operation_id", sa.String(length=255), nullable=False),
        sa.Column("spec", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("job_id", "operation_id", name="uq_job_viz_job_op"),
    )


def downgrade() -> None:
    op.drop_table("job_visualizations")
