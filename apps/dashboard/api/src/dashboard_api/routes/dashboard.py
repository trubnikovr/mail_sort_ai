from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mail_sort_database.models import Alert, AuditLog, Destination, EmailRecord, Job

from ..auth import require_admin
from ..dependencies import get_session
from .serializers import job_summary

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/dashboard/summary")
def get_dashboard_summary(session: Session = Depends(get_session)) -> dict[str, Any]:
    counts = {
        status: count
        for status, count in session.execute(
            select(Job.status, func.count()).group_by(Job.status)
        ).all()
    }
    recent = session.execute(
        select(Job, EmailRecord)
        .outerjoin(EmailRecord, Job.email_record_id == EmailRecord.id)
        .order_by(Job.created_at.desc())
        .limit(8)
    ).all()
    recent_job_ids = [job.id for job, _ in recent]
    destination_by_job: dict[Any, str] = {}
    if recent_job_ids:
        audit_rows = session.execute(
            select(AuditLog.job_id, AuditLog.details)
            .where(AuditLog.job_id.in_(recent_job_ids))
            .order_by(AuditLog.created_at.desc())
        ).all()
        for audit_job_id, details in audit_rows:
            destination = details.get("destination_id")
            if audit_job_id not in destination_by_job and isinstance(destination, str):
                destination_by_job[audit_job_id] = destination
    return {
        "jobs": {
            "total": sum(counts.values()),
            "pending": counts.get("pending", 0),
            "processing": counts.get("processing", 0),
            "completed": counts.get("completed", 0),
            "review": counts.get("review", 0),
            "failed": counts.get("failed", 0),
        },
        "destinations": session.scalar(
            select(func.count()).select_from(Destination).where(Destination.is_active.is_(True))
        ) or 0,
        "pending_alerts": session.scalar(
            select(func.count()).select_from(Alert).where(Alert.status == "pending")
        ) or 0,
        "recent_jobs": [
            job_summary(job, email, destination_by_job.get(job.id))
            for job, email in recent
        ],
    }
