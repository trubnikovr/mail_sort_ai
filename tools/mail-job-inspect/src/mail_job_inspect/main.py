import argparse
from datetime import datetime
from os import environ, getenv
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from mail_sort_database.models import AiRequest, AuditLog, Job, JobEvent
from mail_sort_database.session import create_session_factory, session_scope


def _load_local_env() -> None:
    env_file = Path(__file__).resolve().parents[4] / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if separator and key.strip():
            environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _time(value: datetime | None) -> str:
    return value.isoformat(timespec="seconds") if value else "-"


def _safe_details(details: dict) -> str:
    allowed = ("source", "destination_id", "confidence", "reason", "error_type", "tokens", "validation")
    values = [f"{key}={details[key]}" for key in allowed if details.get(key) is not None]
    return " ".join(values)


def main() -> None:
    parser = argparse.ArgumentParser(description="Show concise database history for a Mail Sort job")
    parser.add_argument("job_id", help="Job UUID")
    arguments = parser.parse_args()
    try:
        job_id = UUID(arguments.job_id)
    except ValueError:
        parser.error("job_id must be a UUID")

    _load_local_env()
    database_url = getenv("DATABASE_URL", "").strip()
    if not database_url:
        parser.error("DATABASE_URL is not set and was not found in the project .env file")

    with session_scope(create_session_factory(database_url)) as session:
        root = session.get(Job, job_id)
        if root is None:
            parser.error(f"job not found: {job_id}")

        jobs = [root]
        # Follow route jobs created by this classification and any parent classification
        # referenced by a route job, so either ID can be used for lookup.
        related = session.scalars(
            select(Job).where(Job.payload["classification_job_id"].astext == str(root.id))
        ).all()
        jobs.extend(related)
        if root.type == "route_email":
            parent_id = root.payload.get("classification_job_id")
            try:
                parent = session.get(Job, UUID(parent_id)) if parent_id else None
            except (ValueError, TypeError):
                parent = None
            if parent is not None:
                jobs.insert(0, parent)

        job_ids = list(dict.fromkeys(job.id for job in jobs))
        print("JOBS")
        for job in jobs:
            print(
                f"{job.id} {job.type} status={job.status} attempts={job.attempts}/{job.max_attempts} "
                f"created={_time(job.created_at)} completed={_time(job.completed_at)}"
            )
            if job.last_error:
                print(f"  last_error: {job.last_error}")

        audits = session.scalars(
            select(AuditLog).where(AuditLog.job_id.in_(job_ids)).order_by(AuditLog.created_at)
        ).all()
        print("AUDIT")
        for item in audits:
            summary = _safe_details(item.details or {})
            if item.error:
                summary = f"{summary} error={item.error}".strip()
            print(f"{_time(item.created_at)} job={item.job_id} action={item.action} {summary}".rstrip())

        for label, model in (("EVENTS", JobEvent), ("AI REQUESTS", AiRequest)):
            entries = session.scalars(
                select(model).where(model.job_id.in_(job_ids)).order_by(model.created_at)
            ).all()
            print(label)
            for item in entries:
                summary = _safe_details(item.details or {})
                print(
                    f"{_time(item.created_at)} job={item.job_id} attempt={item.attempt} "
                    f"step={item.step} status={item.status} {summary}".rstrip()
                )


if __name__ == "__main__":
    main()
