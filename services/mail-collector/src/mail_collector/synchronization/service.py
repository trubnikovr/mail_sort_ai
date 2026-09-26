from mail_sort_contracts import ClassifyEmailJob

from mail_collector.mailboxes.models import CursorExpiredError, MailboxAccount
from mail_collector.mailboxes.registry import MailboxSourceRegistry

from .ports import EmailJobPublisherPort, EmailRecordStorePort, MailboxCursorStorePort


class MailboxSynchronizationService:
    """Coordinates a provider strategy, durable jobs, and provider cursor."""

    def __init__(
        self,
        mail_sources: MailboxSourceRegistry,
        job_publisher: EmailJobPublisherPort,
        cursor_store: MailboxCursorStorePort,
        email_records: EmailRecordStorePort,
    ) -> None:
        self._mail_sources = mail_sources
        self._job_publisher = job_publisher
        self._cursor_store = cursor_store
        self._email_records = email_records

    def synchronize(self, account: MailboxAccount) -> int:
        source = self._mail_sources.for_account(account)
        cursor = self._cursor_store.get(account.id)
        try:
            page = source.collect(account, cursor)
        except CursorExpiredError:
            page = source.collect(account, cursor=None)

        for message in page.messages:
            email_record_id = self._email_records.upsert(account, message)
            self._job_publisher.publish(
                ClassifyEmailJob(
                    account_id=account.id,
                    provider=account.provider,
                    provider_message_id=message.provider_message_id,
                    idempotency_key=f"{account.id}:{message.provider_message_id}",
                    email_record_id=email_record_id,
                )
            )
        # Advance only after all jobs are durable. Replays are safe via the key.
        self._cursor_store.save(account.id, page.next_cursor)
        self._email_records.delete_expired()
        return len(page.messages)
