from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import String, cast, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AuditAction, SubmissionStatus, Submission, SubmissionRecord, User, normalize_submission_status
from app.services.agent_dispatcher import enqueue_submission_dispatch
from app.services.audit import log_action
from app.services.websocket_manager import ws_manager


def is_quarantined_submission(submission: Submission) -> bool:
    status_str = normalize_submission_status(submission.status)
    payload = submission.summary if isinstance(submission.summary, dict) else {}
    payload_status = str(payload.get("status", "")).strip().lower()
    if status_str == SubmissionStatus.quarantined.value:
        return True
    return status_str == SubmissionStatus.queued.value and payload_status in {"pending_agent_availability", "rejected"}


def build_quarantine_title(submission: Submission) -> str:
    instruction = (submission.instruction or "").strip()
    if instruction:
        return instruction[:72] + ("..." if len(instruction) > 72 else "")
    return submission.file_name


def _requeue_blocked_detail(submission: Submission) -> str:
    normalized_status = normalize_submission_status(submission.status)
    payload = submission.summary if isinstance(submission.summary, dict) else {}
    payload_status = str(payload.get("status", "")).strip().lower() or "none"
    return (
        "This workflow cannot be requeued right now "
        f"(submission_status={normalized_status!r}, payload_status={payload_status!r})."
    )


async def list_quarantined_submissions(db: AsyncSession) -> list[Submission]:
    payload_status = func.coalesce(Submission.summary["status"].astext, "")
    return (
        await db.execute(
            select(Submission)
            .options(selectinload(Submission.user), selectinload(Submission.review))
            .where(
                cast(Submission.status, String).in_([SubmissionStatus.quarantined.value, SubmissionStatus.queued.value]),
                payload_status.in_(["pending_agent_availability", "rejected"]),
            )
            .order_by(Submission.uploaded_at.desc())
        )
    ).scalars().all()


async def requeue_submission(
    db: AsyncSession,
    *,
    submission: Submission,
    actor: User | None = None,
    preferred_agent_name: str | None = None,
    clear_existing_output: bool = True,
) -> Submission:
    if normalize_submission_status(submission.status) not in {
        SubmissionStatus.queued.value,
        SubmissionStatus.failed.value,
        SubmissionStatus.succeeded.value,
        SubmissionStatus.quarantined.value,
        SubmissionStatus.declined.value,
    } and not is_quarantined_submission(submission):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_requeue_blocked_detail(submission),
        )

    submission.status = SubmissionStatus.queued
    submission.agent_task_id = None
    submission.dispatched_at = None
    submission.completed_at = None
    submission.summary = None
    submission.preferred_agent_name = preferred_agent_name.strip() if preferred_agent_name else None
    if clear_existing_output:
        submission.output_path = None

    await db.execute(delete(SubmissionRecord).where(SubmissionRecord.submission_id == submission.id))
    await db.commit()
    await db.refresh(submission)

    if actor:
        await log_action(
            db,
            actor,
            AuditAction.reupload_submitted,
            target_id=submission.id,
            target_label=submission.file_name,
            detail=(
                "workflow_requeued"
                if not preferred_agent_name
                else f"workflow_assigned:{preferred_agent_name.strip()}"
            ),
        )

    payload = {
        "upload_id": submission.id,
        "filename": submission.file_name,
        "status": normalize_submission_status(submission.status),
        "agent_status": normalize_submission_status(submission.status),
        "preferred_agent_name": submission.preferred_agent_name,
        "title": build_quarantine_title(submission),
    }
    await ws_manager.broadcast("uploads", "upload_status", payload)
    await ws_manager.broadcast("uploads", "upload.processing", payload)
    await ws_manager.broadcast("dashboard", "dashboard_refresh", payload)
    await ws_manager.broadcast("manager", "upload_reviewed", payload)

    await enqueue_submission_dispatch(submission.id)
    return submission


async def requeue_quarantined_submissions(db: AsyncSession, *, actor: User | None = None) -> list[UUID]:
    quarantined = await list_quarantined_submissions(db)
    requeued_ids: list[UUID] = []
    for submission in quarantined:
        try:
            await requeue_submission(db, submission=submission, actor=actor)
            requeued_ids.append(submission.id)
        except Exception:
            continue
    return requeued_ids
