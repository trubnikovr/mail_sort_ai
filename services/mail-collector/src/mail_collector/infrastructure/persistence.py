from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, exists, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from mail_sort_contracts import ClassifyEmailJob
from mail_sort_database.models import EmailRecord, Job, MailboxCursor
from mail_sort_database.session import session_scope

from mail_collector.mailboxes.models import DiscoveredMessage, MailboxAccount
from mail_collector.synchronization.ports import (
    EmailJobPublisherPort,
    EmailRecordStorePort,
    MailboxCursorStorePort,
)


class EmailJobPublisher(EmailJobPublisherPort):
    """Persists an idempotent job and wakes processors in one transaction."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def publish(self, job: ClassifyEmailJob) -> None:
        statement = (
            insert(Job)
            .values(
                id=uuid4(),
                type=job.type,
                account_id=job.account_id,
                provider=job.provider,
                provider_message_id=job.provider_message_id,
                idempotency_key=job.idempotency_key,
                email_record_id=UUID(job.email_record_id),
                payload={
                    "account_id": job.account_id,
                    "provider": job.provider,
                    "provider_message_id": job.provider_message_id,
                    "email_record_id": job.email_record_id,
                },
            )
            .on_conflict_do_nothing(index_elements=[Job.idempotency_key])
        )
        with session_scope(self._sessions) as session:
            result = session.execute(statement)
            if result.rowcount:
                session.execute(text("SELECT pg_notify('mail_jobs', 'new')"))


class MailboxCursorStore(MailboxCursorStorePort):
    """Stores the last durable IMAP UID for each mailbox account."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def get(self, account_id: str) -> str | None:
        with session_scope(self._sessions) as session:
            return session.scalar(
                select(MailboxCursor.cursor).where(MailboxCursor.account_id == account_id)
            )

    def save(self, account_id: str, cursor: str) -> None:
        now = datetime.now(UTC)
        statement = (
            insert(MailboxCursor)
            .values(account_id=account_id, cursor=cursor, updated_at=now)
            .on_conflict_do_update(
                index_elements=[MailboxCursor.account_id],
                set_={"cursor": cursor, "updated_at": now},
            )
        )
        with session_scope(self._sessions) as session:
            session.execute(statement)


class EmailRecordStore(EmailRecordStorePort):
    """Stores one normalized email snapshot for seven days."""

    _RETENTION_DAYS = 7

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def upsert(self, account: MailboxAccount, message: DiscoveredMessage) -> str:
        now = datetime.now(UTC)
        expires_at = now.replace(microsecond=0) + timedelta(days=self._RETENTION_DAYS)
        statement = (
            insert(EmailRecord)
            .values(
                id=uuid4(),
                account_id=account.id,
                provider_message_id=message.provider_message_id,
                subject=message.headers.get("subject", ""),
                headers=message.headers,
                body=message.body,
                received_at=message.received_at,
                expires_at=expires_at,
            )
            .on_conflict_do_update(
                index_elements=[EmailRecord.account_id, EmailRecord.provider_message_id],
                set_={
                    "subject": message.headers.get("subject", ""),
                    "headers": message.headers,
                    "body": message.body,
                    "received_at": message.received_at,
                    "expires_at": expires_at,
                },
            )
            .returning(EmailRecord.id)
        )
        with session_scope(self._sessions) as session:
            return str(session.scalar(statement))

    def delete_expired(self) -> int:
        active_job_exists = exists(
            select(Job.id).where(
                Job.email_record_id == EmailRecord.id,
                Job.status.in_(("pending", "processing")),
            )
        )
        statement = delete(EmailRecord).where(
            EmailRecord.expires_at < datetime.now(UTC),
            ~active_job_exists,
        )
        with session_scope(self._sessions) as session:
            result = session.execute(statement)
            return result.rowcount
