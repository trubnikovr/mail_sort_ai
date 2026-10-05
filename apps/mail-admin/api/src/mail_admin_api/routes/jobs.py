from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, or_, select
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
    )
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
    return {"items": [job_summary(job, email) for job, email in jobs], "limit": limit, "offset": offset}


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
    details["payload"] = job.payload
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
