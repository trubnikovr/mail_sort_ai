from mail_sort_alerts import AlertEvent, AlertSeverity
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session, sessionmaker

from mail_sort_database.models import AiDailyUsage, Alert, AppSetting, AuditLog, Destination, Job
from mail_sort_database.session import session_scope
from sqlalchemy.dialects.postgresql import insert
import logging

from mail_sort_contracts import MailProvider, RouteEmailJob
from mail_decision.processing.context import ClaimedEmailJob, ProcessingOutcome
from mail_decision.processing.ports import (
    AiRequestQuota,
    ClassificationResultStore,
    DecisionControl,
    DestinationRepository as DestinationRepositoryPort,
    ProcessingFailureHandler,
)
from mail_decision.processing.worker import JobClaimer

logger = logging.getLogger(__name__)


class JobStore(ClassificationResultStore, JobClaimer, ProcessingFailureHandler):
    """Claims jobs atomically and persists their terminal or retry state."""

    def __init__(self, sessions: sessionmaker[Session], worker_id: str) -> None:
        self._sessions = sessions
        self._worker_id = worker_id

    def claim_next(self) -> ClaimedEmailJob | None:
        job = self._claim_next("classify_email")
        if job is None:
            return None
        return ClaimedEmailJob(
            id=str(job.id),
            account_id=job.account_id,
            provider_message_id=job.provider_message_id,
            email_record_id=str(job.email_record_id),
            attempt=job.attempts,
        )

    def _claim_next(self, job_type: str) -> Job | None:
        now = datetime.now(UTC)
        statement = (
            select(Job)
            .where(
                Job.type == job_type,
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
            job.status = "processing"
            job.attempts += 1
            job.locked_at = now
            job.locked_by = self._worker_id
            job.last_error = None
            session.flush()
            return job

    def recover_stale(self, timeout_seconds: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
        statement = (
            select(Job)
            .where(
                Job.type == "classify_email",
                Job.status == "processing",
                Job.locked_at < cutoff,
            )
            .with_for_update(skip_locked=True)
        )
        with session_scope(self._sessions) as session:
            jobs = session.scalars(statement).all()
            now = datetime.now(UTC)
            for job in jobs:
                job.locked_at = None
                job.locked_by = None
                if job.attempts >= job.max_attempts:
                    job.status = "failed"
                    job.completed_at = now
                    event = AlertEvent(
                        deduplication_key=f"job-failed:{job.id}",
                        source="mail-decision",
                        title="Classification job exhausted retries",
                        message=f"Job {job.id} was abandoned after {job.attempts} attempts.",
                        context={"job_id": str(job.id), "account_id": job.account_id,
                                 "provider": job.provider, "provider_message_id": job.provider_message_id},
                    )
                    session.add(Alert(
                        deduplication_key=event.deduplication_key, source=event.source,
                        severity=event.severity.value, title=event.title, message=event.message,
                        context=event.context,
                    ))
                else:
                    job.status = "pending"
            return len(jobs)

    def finalize(self, job: ClaimedEmailJob, outcome: ProcessingOutcome) -> None:
        """Write audit data and enqueue a route in the same transaction."""
        now = datetime.now(UTC)
        with session_scope(self._sessions) as session:
            classification_job = session.get(Job, UUID(job.id), with_for_update=True)
            if (
                classification_job is None
                or classification_job.type != "classify_email"
                or classification_job.status != "processing"
            ):
                raise LookupError(f"Processing classification job {job.id} was not found")

            session.add(
                AuditLog(
                    id=uuid4(),
                    job_id=classification_job.id,
                    action=outcome.status,
                    details={
                        "source": outcome.source,
                        "destination_id": outcome.destination_id,
                        "confidence": outcome.confidence,
                        "reason": outcome.reason,
                    },
                )
            )
            if outcome.status in {"completed", "review"} and outcome.destination_id is not None:
                route = RouteEmailJob(
                    account_id=classification_job.account_id,
                    provider=cast(MailProvider, classification_job.provider),
                    provider_message_id=classification_job.provider_message_id,
                    email_record_id=str(classification_job.email_record_id),
                    idempotency_key=f"{classification_job.id}:route",
                    action="move",
                    destination_id=outcome.destination_id,
                    classification_job_id=str(classification_job.id),
                )
                statement = (
                    insert(Job)
                    .values(
                        id=uuid4(),
                        type=route.type,
                        account_id=route.account_id,
                        provider=route.provider,
                        provider_message_id=route.provider_message_id,
                        idempotency_key=route.idempotency_key,
                        email_record_id=UUID(route.email_record_id),
                        payload={
                            "action": route.action,
                            "destination_id": route.destination_id,
                            "classification_job_id": route.classification_job_id,
                        },
                    )
                    .on_conflict_do_nothing(index_elements=[Job.idempotency_key])
                )
                result = session.execute(statement)
                if result.rowcount:
                    session.execute(text("SELECT pg_notify('mail_jobs', 'new')"))
            classification_job.status = outcome.status
            if outcome.status == "review":
                classification_job.last_error = outcome.reason
            classification_job.locked_at = None
            classification_job.locked_by = None
            classification_job.completed_at = now

    def defer(self, job_id: str, error: Exception, delay_seconds: int) -> None:
        with session_scope(self._sessions) as session:
            job = session.get(Job, UUID(job_id), with_for_update=True)
            if job is None or job.status != "processing" or job.locked_by != self._worker_id:
                raise LookupError(f"Owned processing job {job_id} was not found")
            job.status = "pending"
            job.attempts = max(0, job.attempts - 1)
            job.last_error = str(error)[:4000]
            job.locked_at = None
            job.locked_by = None
            job.retry_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)

    def pause_for_billing_failure(self, job_id: str, provider: str, error_code: str) -> None:
        should_create_alert = False
        setting_saved = False
        try:
            with session_scope(self._sessions) as session:
                setting = session.get(AppSetting, "mail_decision.enabled", with_for_update=True)
                if setting is None:
                    should_create_alert = True
                    session.add(AppSetting(
                        key="mail_decision.enabled",
                        value=False,
                        description="Controls whether Decision claims new classification jobs.",
                    ))
                else:
                    should_create_alert = setting.value is not False
                    setting.value = False
            setting_saved = True
        except Exception:
            logger.exception(
                "failed to disable decision after AI billing failure: job_id=%s provider=%s code=%s",
                job_id, provider, error_code,
            )

        job_released = False
        try:
            with session_scope(self._sessions) as session:
                job = session.get(Job, UUID(job_id), with_for_update=True)
                if job is None or job.status != "processing" or job.locked_by != self._worker_id:
                    raise LookupError(f"Owned processing job {job_id} was not found")
                job.status = "pending"
                job.attempts = max(0, job.attempts - 1)
                job.retry_at = datetime.now(UTC)
                job.last_error = f"AI billing limit: provider={provider} code={error_code}"[:4000]
                job.locked_at = None
                job.locked_by = None
                job.completed_at = None
            job_released = True
        except Exception:
            logger.exception(
                "failed to release job after AI billing failure: job_id=%s provider=%s code=%s",
                job_id, provider, error_code,
            )

        alert_saved = not should_create_alert
        if should_create_alert:
            try:
                self._create_billing_alert(job_id, provider, error_code)
                alert_saved = True
            except Exception:
                logger.exception(
                    "failed to queue AI billing alert: job_id=%s provider=%s code=%s",
                    job_id, provider, error_code,
                )

        if not (setting_saved and job_released and alert_saved):
            raise RuntimeError(
                "AI billing failure handling was incomplete "
                f"(setting_saved={setting_saved}, job_released={job_released}, "
                f"alert_saved={alert_saved})"
            )

    def _create_billing_alert(self, job_id: str, provider: str, error_code: str) -> None:
        with session_scope(self._sessions) as session:
            job = session.get(Job, UUID(job_id))
            context = {
                "provider": provider,
                "error_code": error_code,
                "job_id": job_id,
                "account_id": job.account_id if job else None,
                "provider_message_id": job.provider_message_id if job else None,
            }
            event = AlertEvent(
                deduplication_key=f"ai-billing-unavailable:{provider}:{uuid4()}",
                source="mail-decision",
                title="AI billing limit reached; classification paused",
                message=(
                    f"Decision was paused after {provider} reported billing/quota code "
                    f"{error_code}. Resolve the provider billing limit, then resume Decision "
                    "from the admin dashboard."
                ),
                severity=AlertSeverity.CRITICAL,
                context=context,
            )
            statement = insert(Alert).values(
                id=uuid4(),
                deduplication_key=event.deduplication_key,
                source=event.source,
                severity=event.severity.value,
                title=event.title,
                message=event.message,
                context=event.context,
            ).on_conflict_do_nothing(index_elements=[Alert.deduplication_key])
            session.execute(statement)

    def retry(self, job_id: str, error: Exception, retry_delay_seconds: int) -> None:
        now = datetime.now(UTC)
        with session_scope(self._sessions) as session:
            job = session.get(Job, UUID(job_id), with_for_update=True)
            if job is None:
                raise LookupError(f"Job {job_id} was not found")
            job.last_error = str(error)[:4000]
            job.locked_at = None
            job.locked_by = None
            if job.attempts >= job.max_attempts:
                job.status = "failed"
                job.completed_at = now
                event = AlertEvent(
                    deduplication_key=f"job-failed:{job.id}",
                    source="mail-decision",
                    severity=AlertSeverity.CRITICAL,
                    title="Classification job exhausted retries",
                    message=(
                        f"Job {job.id}, provider message {job.provider_message_id}, failed after "
                        f"{job.attempts} attempts ({type(error).__name__})."
                    ),
                    context={"job_id": str(job.id), "account_id": job.account_id,
                             "provider": job.provider, "provider_message_id": job.provider_message_id},
                )
                session.add(Alert(
                    deduplication_key=event.deduplication_key,
                    source=event.source,
                    severity=event.severity.value,
                    title=event.title,
                    message=event.message,
                    context=event.context,
                ))
            else:
                job.status = "pending"
                job.retry_at = now + timedelta(seconds=retry_delay_seconds)

    def _set_terminal_status(
        self,
        job_id: str,
        job_type: str,
        status: str,
        last_error: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        statement = (
            update(Job)
            .where(
                Job.id == UUID(job_id),
                Job.type == job_type,
                Job.status == "processing",
            )
            .values(
                status=status,
                last_error=last_error,
                locked_at=None,
                locked_by=None,
                completed_at=now,
            )
        )
        with session_scope(self._sessions) as session:
            if not session.execute(statement).rowcount:
                raise LookupError(f"Processing {job_type} job {job_id} was not found")


class DestinationRepository(DestinationRepositoryPort):
    """Read active AI destinations and their instructions from PostgreSQL."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def active_for_account(self, account_id: str) -> dict[str, str]:
        statement = select(Destination).where(
            Destination.account_id == account_id,
            Destination.is_active.is_(True),
            Destination.use_for_ai.is_(True),
        ).order_by(Destination.name)
        with session_scope(self._sessions) as session:
            destinations = session.scalars(statement).all()
            return {
                destination.id: (
                    f"{destination.name} — {destination.instruction}"
                    if destination.instruction else destination.name
                )
                for destination in destinations
            }


class DailyAiRequestQuota(AiRequestQuota):
    """Atomically acquires one request permit within the configured daily cap."""

    def __init__(self, sessions: sessionmaker[Session], max_requests_per_day: int) -> None:
        self._sessions = sessions
        self._max_requests_per_day = max_requests_per_day

    def acquire(self, provider: str) -> bool:
        statement = (
            insert(AiDailyUsage)
            .values(provider=provider, usage_date=datetime.now(UTC).date(), request_count=1)
            .on_conflict_do_update(
                index_elements=[AiDailyUsage.provider, AiDailyUsage.usage_date],
                set_={"request_count": AiDailyUsage.request_count + 1},
                where=AiDailyUsage.request_count < self._max_requests_per_day,
            )
            .returning(AiDailyUsage.request_count)
        )
        with session_scope(self._sessions) as session:
            return session.scalar(statement) is not None


class DatabaseDecisionControl(DecisionControl):
    """Reads the shared runtime switch before Decision claims each new job."""

    SETTING_KEY = "mail_decision.enabled"

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def is_enabled(self) -> bool:
        with session_scope(self._sessions) as session:
            setting = session.get(AppSetting, self.SETTING_KEY)
            return setting is None or setting.value is not False
