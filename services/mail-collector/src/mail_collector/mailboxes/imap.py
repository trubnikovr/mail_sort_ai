from collections.abc import Callable
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
import imaplib

from .email_body import extract_body
from .models import DiscoveredMessage, MailboxAccount, SyncPage
from .port import MailboxSource
from .recent_mail_policy import RecentMailPolicy


class ImapMailboxSource(MailboxSource):
    """IMAP adapter that uses monotonic UIDs as its sync cursor."""

    def __init__(
        self,
        connection_factory: Callable[[MailboxAccount], imaplib.IMAP4],
        recent_mail: RecentMailPolicy | None = None,
    ) -> None:
        # The factory owns TLS, authentication, and secret retrieval.
        self._connection_factory = connection_factory
        self._recent_mail = recent_mail or RecentMailPolicy()

    def collect(self, account: MailboxAccount, cursor: str | None) -> SyncPage:
        last_uid = int(cursor or "0")
        session = self._connection_factory(account)
        try:
            status, _ = session.select(account.mailbox, readonly=True)
            if status != "OK":
                raise RuntimeError(f"Could not select IMAP mailbox {account.mailbox!r}")
            status, data = session.uid(
                "SEARCH",
                None,
                f"UID {last_uid + 1}:* SINCE {self._recent_mail.imap_since_criterion()}",
            )
            if status != "OK":
                raise RuntimeError("IMAP UID SEARCH failed")
            uids = [int(value) for value in data[0].split()] if data and data[0] else []
            messages = tuple(self._read_message(session, uid) for uid in uids)
        finally:
            session.logout()

        next_cursor = str(max(uids, default=last_uid))
        return SyncPage(messages=messages, next_cursor=next_cursor)

    @staticmethod
    def _read_message(session: imaplib.IMAP4, uid: int) -> DiscoveredMessage:
        status, data = session.uid("FETCH", str(uid), "(BODY.PEEK[])")
        if status != "OK" or not data or not isinstance(data[0], tuple):
            raise RuntimeError(f"IMAP UID FETCH failed for message {uid}")
        raw_email = data[0][1]
        message = BytesParser(policy=policy.default).parsebytes(raw_email)
        headers = {
            "from": str(message.get("From", "")),
            "to": str(message.get("To", "")),
            "subject": str(message.get("Subject", "")),
            "date": str(message.get("Date", "")),
            "message_id": str(message.get("Message-ID", "")),
        }
        return DiscoveredMessage(
            provider_message_id=str(uid),
            headers=headers,
            body=extract_body(message),
            received_at=ImapMailboxSource._received_at(message),
        )

    @staticmethod
    def _received_at(message: object) -> datetime | None:
        date = getattr(message, "get")("Date")
        if not date:
            return None
        try:
            from email.utils import parsedate_to_datetime

            parsed = parsedate_to_datetime(date)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except (TypeError, ValueError, IndexError):
            return None
