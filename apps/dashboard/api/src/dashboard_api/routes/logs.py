from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, case, cast, func, literal, or_, select, union_all
from sqlalchemy.orm import Session

from mail_sort_database.models import AiRequest, AuditLog, EmailRecord, Job, JobEvent, SystemLog

from ..auth import require_admin
from ..dependencies import get_session

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/logs")
def list_logs(
    q: str = Query(default="", max_length=256),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    term = f"%{q.strip()}%" if q.strip() else None

    def searchable(statement: Any, details: Any) -> Any:
        if term is None:
            return statement
        return statement.where(or_(
            Job.provider_message_id.ilike(term),
            cast(Job.id, String).ilike(term),
            EmailRecord.subject.ilike(term),
            cast(details, String).ilike(term),
        ))

    common = (
        Job.provider_message_id,
        EmailRecord.subject,
    )
    step_events = searchable(
        select(
            JobEvent.id.label("id"),
            JobEvent.job_id.label("job_id"),
            JobEvent.created_at.label("created_at"),
            literal("step").label("source"),
            JobEvent.step.label("event"),
            JobEvent.status.label("status"),
            JobEvent.details.label("details"),
            literal(None, type_=String()).label("error"),
            *common,
        ).select_from(JobEvent).join(Job, Job.id == JobEvent.job_id).outerjoin(
            EmailRecord, Job.email_record_id == EmailRecord.id
        ),
        JobEvent.details,
    )
    ai_events = searchable(
        select(
            AiRequest.id.label("id"),
            AiRequest.job_id.label("job_id"),
            AiRequest.created_at.label("created_at"),
            literal("ai").label("source"),
            AiRequest.step.label("event"),
            AiRequest.status.label("status"),
            AiRequest.details.label("details"),
            literal(None, type_=String()).label("error"),
            *common,
        ).select_from(AiRequest).join(Job, Job.id == AiRequest.job_id).outerjoin(
            EmailRecord, Job.email_record_id == EmailRecord.id
        ),
        AiRequest.details,
    )
    audit_events = searchable(
        select(
            AuditLog.id.label("id"),
            AuditLog.job_id.label("job_id"),
            AuditLog.created_at.label("created_at"),
            literal("audit").label("source"),
            AuditLog.action.label("event"),
            case((AuditLog.error.is_not(None), "error"), else_="success").label("status"),
            AuditLog.details.label("details"),
            AuditLog.error.label("error"),
            *common,
        ).select_from(AuditLog).join(Job, Job.id == AuditLog.job_id).outerjoin(
            EmailRecord, Job.email_record_id == EmailRecord.id
        ),
        AuditLog.details,
    )

    entries = union_all(step_events, ai_events, audit_events).subquery("processing_logs")
    total = session.scalar(select(func.count()).select_from(entries)) or 0
    rows = session.execute(
        select(entries)
        .order_by(entries.c.created_at.desc(), entries.c.id.desc())
        .limit(limit)
        .offset(offset)
    ).mappings().all()
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/system-logs")
def list_system_logs(
    q: str = Query(default="", max_length=256),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    statement = select(SystemLog)
    term = f"%{q.strip()}%" if q.strip() else None
    if term is not None:
        statement = statement.where(or_(
            SystemLog.message.ilike(term),
            SystemLog.exception.ilike(term),
            SystemLog.service.ilike(term),
            SystemLog.logger.ilike(term),
            cast(SystemLog.context, String).ilike(term),
        ))

    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = session.scalars(
        statement.order_by(SystemLog.created_at.desc(), SystemLog.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "items": [{
            "id": str(row.id),
            "created_at": row.created_at,
            "level": row.level.lower(),
            "service": row.service,
            "logger": row.logger,
            "message": row.message,
            "exception": row.exception,
            "context": row.context,
        } for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
