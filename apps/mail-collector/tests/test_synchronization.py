import unittest
from datetime import UTC, datetime

from mail_collector.mailboxes.models import DiscoveredMessage, MailboxAccount, SyncPage
from mail_collector.mailboxes.registry import MailboxSourceRegistry
from mail_collector.synchronization.service import MailboxSynchronizationService


class _Collector:
    def collect(self, account: MailboxAccount, cursor: str | None) -> SyncPage:
        return SyncPage(
            messages=(
                DiscoveredMessage("message-1", {"subject": "One"}, "body", datetime.now(UTC)),
                DiscoveredMessage("message-2", {"subject": "Two"}, "body", datetime.now(UTC)),
            ),
            next_cursor="next",
        )


class _Publisher:
    def __init__(self) -> None:
        self.jobs = []

    def publish(self, job: object) -> None:
        self.jobs.append(job)


class _CursorStore:
    def __init__(self) -> None:
        self.saved = []

    def get(self, account_id: str) -> str | None:
        return "previous"

    def save(self, account_id: str, cursor: str) -> None:
        self.saved.append((account_id, cursor))


class _EmailRecords:
    def __init__(self) -> None:
        self.stored = []
        self.cleanup_calls = 0

    def upsert(self, account: MailboxAccount, message: DiscoveredMessage) -> str:
        self.stored.append((account.id, message.provider_message_id))
        return f"record-{message.provider_message_id}"

    def delete_expired(self) -> int:
        self.cleanup_calls += 1
        return 0


class SynchronizationTest(unittest.TestCase):
    def test_publishes_idempotent_jobs_before_advancing_cursor(self) -> None:
        publisher = _Publisher()
        cursors = _CursorStore()
        email_records = _EmailRecords()
        service = MailboxSynchronizationService(
            mail_sources=MailboxSourceRegistry([("imap", _Collector())]),
            job_publisher=publisher,
            cursor_store=cursors,
            email_records=email_records,
        )

        count = service.synchronize(MailboxAccount(id="account", provider="imap"))

        self.assertEqual(count, 2)
        self.assertEqual([job.idempotency_key for job in publisher.jobs], ["account:message-1", "account:message-2"])
        self.assertEqual(cursors.saved, [("account", "next")])
        self.assertEqual(email_records.stored, [("account", "message-1"), ("account", "message-2")])
        self.assertEqual(email_records.cleanup_calls, 1)
