from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, or_, select, text
from sqlalchemy.orm import Session

from mail_sort_database.models import AuditLog, EmailRecord, Job

from ..auth import require_admin
from ..dependencies import get_session
from .serializers import job_summary

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/jobs")
def list_jobs(
    q: str = Query(default="", max_length=256),
    status: str = Query(default="", max_length=32),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    statement = select(Job, EmailRecord).outerjoin(
        EmailRecord, Job.email_record_id == EmailRecord.id
    ).where(Job.type == "classify_email")
    if status:
        statement = statement.where(Job.status == status)
    if q.strip():
        term = f"%{q.strip()}%"
        statement = statement.where(or_(
            EmailRecord.subject.ilike(term),
            Job.provider_message_id.ilike(term),
            cast(EmailRecord.headers, String).ilike(term),
        ))
    jobs = session.execute(
        statement.order_by(Job.created_at.desc()).limit(limit).offset(offset)
    ).all()
    job_ids = [job.id for job, _ in jobs]
    destination_by_job: dict[UUID, str] = {}
    if job_ids:
        audit_rows = session.execute(
            select(AuditLog.job_id, AuditLog.details)
            .where(AuditLog.job_id.in_(job_ids))
            .order_by(AuditLog.created_at.desc())
        ).all()
        for audit_job_id, details in audit_rows:
            destination = details.get("destination_id")
            if audit_job_id not in destination_by_job and isinstance(destination, str):
                destination_by_job[audit_job_id] = destination
    return {
        "items": [job_summary(job, email, destination_by_job.get(job.id)) for job, email in jobs],
        "limit": limit,
        "offset": offset,
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: UUID, session: Session = Depends(get_session)) -> dict[str, Any]:
    result = session.execute(
        select(Job, EmailRecord)
        .outerjoin(EmailRecord, Job.email_record_id == EmailRecord.id)
        .where(Job.id == job_id)
    ).first()
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job, email = result
    audit = session.scalars(
        select(AuditLog).where(AuditLog.job_id == job.id).order_by(AuditLog.created_at)
    ).all()
    details = job_summary(job, email)
    if not details["destination_id"]:
        details["destination_id"] = next(
            (
                item.details.get("destination_id")
                for item in reversed(audit)
                if isinstance(item.details.get("destination_id"), str)
            ),
            None,
        )
    details["payload"] = job.payload
    related_jobs = session.execute(
        select(Job, EmailRecord)
        .outerjoin(EmailRecord, Job.email_record_id == EmailRecord.id)
        .where(Job.email_record_id == job.email_record_id)
        .order_by(Job.created_at.desc())
    ).all() if job.email_record_id is not None else [(job, email)]
    details["jobs"] = [job_summary(related_job, related_email) for related_job, related_email in related_jobs]
    details["email"] = None if email is None else {
        "subject": email.subject,
        "sender": email.headers.get("from", email.headers.get("sender", "")),
        "headers": email.headers,
        "body": email.body,
        "received_at": email.received_at,
        "expires_at": email.expires_at,
    }
    details["audit"] = [{
        "action": item.action,
        "details": item.details,
        "error": item.error,
        "created_at": item.created_at,
    } for item in audit]
    return details


@router.post("/jobs/{job_id}/reclassify", status_code=202)
def reclassify_email(job_id: UUID, session: Session = Depends(get_session)) -> dict[str, str]:
    source = session.get(Job, job_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if source.email_record_id is None:
        raise HTTPException(status_code=409, detail="Email snapshot is no longer available")

    # Serialize manual requests for the same email and prevent duplicate active work.
    email = session.scalar(
        select(EmailRecord)
        .where(EmailRecord.id == source.email_record_id)
        .with_for_update()
    )
    if email is None:
        raise HTTPException(status_code=409, detail="Email snapshot is no longer available")
    active_job = session.scalar(
        select(Job.id)
        .where(
            Job.email_record_id == email.id,
            Job.type == "classify_email",
            Job.status.in_(("pending", "processing")),
        )
        .limit(1)
        .with_for_update()
    )
    if active_job is not None:
        raise HTTPException(status_code=409, detail="Email already has a classification job in progress")
    classification_job = session.scalar(
        select(Job)
        .where(
            Job.email_record_id == email.id,
            Job.type == "classify_email",
        )
        .order_by(Job.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if classification_job is None:
        raise HTTPException(status_code=409, detail="Classification job is not available")
    if classification_job.status in ("pending", "processing"):
        raise HTTPException(status_code=409, detail="Email already has a classification job in progress")
    classification_job.status = "pending"
    classification_job.attempts = 0
    classification_job.retry_at = datetime.now(UTC)
    classification_job.completed_at = None
    classification_job.last_error = None
    session.execute(text("SELECT pg_notify('mail_jobs', 'new')"))
    session.commit()
    return {"job_id": str(classification_job.id), "status": "pending"}
