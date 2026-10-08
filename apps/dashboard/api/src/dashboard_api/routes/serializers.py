from typing import Any

from mail_sort_database.models import EmailRecord, Job


def job_summary(job: Job, email: EmailRecord | None) -> dict[str, Any]:
    headers = email.headers if email is not None else {}
    return {
        "id": str(job.id),
        "type": job.type,
        "status": job.status,
        "provider": job.provider,
        "provider_message_id": job.provider_message_id,
        "subject": email.subject if email is not None else "",
        "sender": headers.get("from", headers.get("sender", "")),
        "received_at": email.received_at if email is not None else None,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "destination_id": job.payload.get("destination_id"),
        "last_error": job.last_error,
    }
