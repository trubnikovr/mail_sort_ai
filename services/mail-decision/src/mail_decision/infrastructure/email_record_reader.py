from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mail_sort_database.models import EmailRecord
from mail_sort_database.session import session_scope

from mail_decision.processing.context import ClaimedEmailJob, EmailContent
from mail_decision.processing.ports import EmailReader


class EmailRecordReader(EmailReader):
    """Reads the collector's stored email snapshot; it never calls IMAP."""

    def __init__(self, sessions: sessionmaker[Session]) -> None:
        self._sessions = sessions

    def read(self, job: ClaimedEmailJob) -> EmailContent:
        statement = select(EmailRecord).where(
            EmailRecord.id == UUID(job.email_record_id),
            EmailRecord.account_id == job.account_id,
        )
        with session_scope(self._sessions) as session:
            record = session.scalar(statement)

        if record is None:
            raise LookupError(f"Email record {job.email_record_id} was not found")

        return EmailContent(
            sender=record.headers.get("from", ""),
            subject=record.subject,
            body=record.body,
        )
