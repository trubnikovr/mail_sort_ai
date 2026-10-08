import logging

from mail_sort_contracts import ClassifyEmailJob

from mail_collector.mailboxes.models import MailboxAccount
from mail_collector.mailboxes.registry import MailboxSourceRegistry

from .ports import EmailJobPublisherPort, EmailRecordStorePort, MailboxAccountReaderPort

logger = logging.getLogger(__name__)


class MailboxSynchronizationService:
    """Coordinates unread mailbox discovery, durable snapshots, and jobs."""

    def __init__(
        self,
        mail_sources: MailboxSourceRegistry,
        job_publisher: EmailJobPublisherPort,
        email_records: EmailRecordStorePort,
        accounts: MailboxAccountReaderPort | None = None,
    ) -> None:
        self._mail_sources = mail_sources
        self._job_publisher = job_publisher
        self._email_records = email_records
        self._accounts = accounts

    def synchronize_active_accounts(self) -> int:
        if self._accounts is None:
            raise RuntimeError("Mailbox account repository is not configured")
        total = 0
        accounts = self._accounts.active_configured()
        failures: list[Exception] = []
        for account in accounts:
            try:
                count = self.synchronize(account)
                total += count
                logger.info(
                    "mailbox synchronization completed: account_id=%s discovered=%s",
                    account.id,
                    count,
                )
            except Exception as error:
                failures.append(error)
                logger.exception("mailbox synchronization failed: account_id=%s", account.id)
        if not accounts:
            logger.info("no active configured mailbox accounts")
        if failures:
            raise RuntimeError(f"Mailbox synchronization failed for {len(failures)} account(s)") from failures[0]
        return total

    def synchronize(self, account: MailboxAccount) -> int:
        source = self._mail_sources.for_account(account)
        page = source.collect(account)

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
        # Repeated unread scans are safe via the unique job idempotency key.
        self._email_records.delete_expired()
        return len(page.messages)
