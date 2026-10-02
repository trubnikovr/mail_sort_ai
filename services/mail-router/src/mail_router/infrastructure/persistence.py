from mail_sort_repositories import DestinationRepository as SharedDestinationRepository
import logging
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from mail_sort_contracts import MailProvider, RouteEmailJob
from mail_sort_database.models import Job
from mail_sort_database.session import session_scope

from mail_router.routing.registry import DestinationMailboxLookup
from mail_router.routing.worker import MailboxActionClaimer
from mail_router.routing.tasks import ClaimedRouteJob


logger = logging.getLogger(__name__)


class RouteJobStore(MailboxActionClaimer):
    """Current SQL persistence adapter for durable route_email jobs."""

    def __init__(self, sessions: sessionmaker[Session], worker_id: str) -> None:
        self._sessions = sessions
        self._worker_id = worker_id

    def claim_next(self) -> ClaimedRouteJob | None:
        now = datetime.now(UTC)
        statement = (
            select(Job)
            .where(
                Job.type == "route_email",
                Job.status == "pending",
                Job.retry_at <= now,
                Job.attempts < Job.max_attempts,
                Job.email_record_id.is_not(None),
            )
            .order_by(Job.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        with session_scope(self._sessions) as session:
            job = session.scalar(statement)
            if job is None:
                return None
            action = job.payload.get("action")
            destination_id = job.payload.get("destination_id")
            classification_job_id = job.payload.get("classification_job_id")
            if (
                action != "move"
                or not isinstance(destination_id, str)
                or not destination_id
                or not isinstance(classification_job_id, str)
                or not classification_job_id
            ):
                raise ValueError(f"Route job {job.id} has an invalid payload")
            route = RouteEmailJob(
                account_id=job.account_id,
                provider=cast(MailProvider, job.provider),
                provider_message_id=job.provider_message_id,
                email_record_id=str(job.email_record_id),
                idempotency_key=job.idempotency_key,
                action="move",
                destination_id=destination_id,
                classification_job_id=classification_job_id,
            )
            job.status = "processing"
            job.attempts += 1
            job.locked_at = now
            job.locked_by = self._worker_id
            job.last_error = None
            return ClaimedRouteJob(
                id=str(job.id),
                account_id=route.account_id,
                provider=route.provider,
                provider_message_id=route.provider_message_id,
                action=route.action,
                destination_id=route.destination_id,
            )

    def recover_stale(self, timeout_seconds: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
        statement = (
            update(Job)
            .where(
                Job.type == "route_email",
                Job.status == "processing",
                Job.locked_at < cutoff,
                Job.attempts < Job.max_attempts,
            )
            .values(status="pending", locked_at=None, locked_by=None)
        )
        with session_scope(self._sessions) as session:
            return session.execute(statement).rowcount

    def complete(self, job_id: str) -> None:
        self._terminal(job_id, "completed")

    def retry(self, job_id: str, error: Exception, retry_delay_seconds: int) -> None:
        now = datetime.now(UTC)
        with session_scope(self._sessions) as session:
            job = session.get(Job, UUID(job_id), with_for_update=True)
            if job is None or job.type != "route_email":
                raise LookupError(f"Route job {job_id} was not found")
            job.last_error = str(error)[:4000]
            job.locked_at = None
            job.locked_by = None
            if job.attempts >= job.max_attempts:
                job.status = "failed"
                job.completed_at = now
            else:
                job.status = "pending"
                job.retry_at = now + timedelta(seconds=retry_delay_seconds)
            status, attempts, max_attempts = job.status, job.attempts, job.max_attempts
            retry_at = job.retry_at if status == "pending" else None
        logger.info(
            "route failure saved: job_id=%s status=%s attempts=%s/%s retry_at=%s",
            job_id, status, attempts, max_attempts, retry_at,
        )

    def _terminal(self, job_id: str, status: str) -> None:
        statement = (
            update(Job)
            .where(Job.id == UUID(job_id), Job.type == "route_email", Job.status == "processing")
            .values(status=status, locked_at=None, locked_by=None, completed_at=datetime.now(UTC))
        )
        with session_scope(self._sessions) as session:
            if not session.execute(statement).rowcount:
                raise LookupError(f"Processing route job {job_id} was not found")


class DestinationRepository(DestinationMailboxLookup):
    """Adapt shared destination records to a mailbox path for routing."""

    def __init__(self, account_id: str) -> None:
        self._repository = SharedDestinationRepository(account_id)

    def mailbox_for(self, account_id: str, destination_id: str) -> str:
        return self._repository.get_active(account_id, destination_id).mailbox
