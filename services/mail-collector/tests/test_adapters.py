import unittest
from datetime import UTC, datetime

from mail_collector.mailboxes.imap import ImapMailboxSource
from mail_collector.mailboxes.models import MailboxAccount
from mail_collector.mailboxes.recent_mail_policy import RecentMailPolicy


NOW = datetime(2026, 9, 24, 12, tzinfo=UTC)


class _ImapSession:
    def __init__(self) -> None:
        self.logged_out = False

    def select(self, mailbox: str, readonly: bool = False) -> tuple[str, list[bytes]]:
        self.mailbox = mailbox
        self.readonly = readonly
        return "OK", []

    def uid(self, command: str, *args: object) -> tuple[str, list[bytes]]:
        self.command = command
        self.args = args
        if command == "SEARCH":
            self.search_args = args
            return "OK", [b"7 8"]
        if command == "FETCH":
            self.fetch_args = args
            return "OK", [
                (
                    b"7 (RFC822 {123}",
                    b"From: billing@example.com\r\n"
                    b"Subject: Invoice\r\n"
                    b"Date: Wed, 24 Sep 2026 12:00:00 +0000\r\n"
                    b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
                    b"Invoice body",
                )
            ]
        raise AssertionError(f"Unexpected IMAP command: {command}")

    def logout(self) -> tuple[str, list[bytes]]:
        self.logged_out = True
        return "BYE", []


class AdapterTest(unittest.TestCase):
    def test_imap_uses_uids_and_advances_cursor(self) -> None:
        session = _ImapSession()
        recent_mail = RecentMailPolicy(now=lambda: NOW)
        result = ImapMailboxSource(lambda _: session, recent_mail=recent_mail).collect(
            MailboxAccount(id="account", provider="imap"), cursor="6"
        )
        self.assertEqual([message.provider_message_id for message in result.messages], ["7", "8"])
        self.assertEqual(result.messages[0].headers["subject"], "Invoice")
        self.assertEqual(result.messages[0].body, "Invoice body")
        self.assertEqual(result.next_cursor, "8")
        self.assertEqual(session.search_args, (None, "UID 7:* SINCE 22-Sep-2026"))
        self.assertEqual(session.fetch_args, ("8", "(BODY.PEEK[])"))
        self.assertTrue(session.logged_out)
