"""
Visualization persistence models and repository functions.

Provides the JobVisualization SQLAlchemy model mapped to the `job_visualizations`
table and async helper functions for upsert and query operations.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID, insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class JobVisualization(Base):
    """Persisted visualization spec for a job execution."""

    __tablename__ = "job_visualizations"
    __table_args__ = (
        UniqueConstraint("job_id", "operation_id", name="uq_job_viz_job_op"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    spec: Mapped[dict] = mapped_column(JSONB, nullable=False)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


async def upsert_visualization(
    db: AsyncSession,
    *,
    job_id: uuid.UUID,
    operation_id: str,
    spec: dict,
    data: dict | None = None,
) -> uuid.UUID:
    """
    Insert a visualization row or update on (job_id, operation_id) conflict.

    On conflict, the existing row's spec, data, and created_at are replaced
    with the new values (Requirements 10.2, 10.3).

    Returns the row id (either newly inserted or existing).
    """
    row_id = uuid.uuid4()
    stmt = pg_insert(JobVisualization).values(
        id=row_id,
        job_id=job_id,
        operation_id=operation_id,
        spec=spec,
        data=data,
        created_at=func.now(),
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_job_viz_job_op",
        set_={
            "spec": stmt.excluded.spec,
            "data": stmt.excluded.data,
            "created_at": stmt.excluded.created_at,
        },
    )
    # Use RETURNING to get the actual id (either new or existing after update)
    stmt = stmt.returning(JobVisualization.id)
    result = await db.execute(stmt)
    returned_id = result.scalar_one()
    await db.commit()
    return returned_id


async def get_visualizations_by_job_id(
    db: AsyncSession,
    job_id: uuid.UUID,
) -> list[JobVisualization]:
    """
    Query all visualization specs for a given job, ordered by created_at ascending.

    Returns an empty list if no visualizations exist for the job.
    """
    stmt = (
        select(JobVisualization)
        .where(JobVisualization.job_id == job_id)
        .order_by(JobVisualization.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
