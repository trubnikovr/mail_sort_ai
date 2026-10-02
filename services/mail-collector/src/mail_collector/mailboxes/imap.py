from collections.abc import Callable
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
import imaplib

from .email_body import extract_body
from .models import DiscoveredMessage, MailboxAccount, SyncPage
from .port import MailboxSource


class ImapMailboxSource(MailboxSource):
    """IMAP adapter that uses monotonic UIDs as its sync cursor."""

    def __init__(
        self,
        connection_factory: Callable[[MailboxAccount], imaplib.IMAP4],
    ) -> None:
        # The factory owns TLS, authentication, and secret retrieval.
        self._connection_factory = connection_factory

    def collect(self, account: MailboxAccount, cursor: str | None) -> SyncPage:
        last_uid = int(cursor or "0")
        session = self._connection_factory(account)
        try:
            status, _ = session.select(account.mailbox, readonly=True)
            if status != "OK":
                raise RuntimeError(f"Could not select IMAP mailbox {account.mailbox!r}")
            if cursor is None:
                # Establish a high-water mark without importing the mailbox backlog.
                status, data = session.uid("SEARCH", None, "ALL")
                if status != "OK":
                    raise RuntimeError("IMAP UID SEARCH for initial cursor failed")
                uids = [int(value) for value in data[0].split()] if data and data[0] else []
                return SyncPage(messages=(), next_cursor=str(max(uids, default=0)))
            status, data = session.uid(
                "SEARCH",
                None,
                f"UNSEEN UID {last_uid + 1}:*",
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
        # Only the top-level report counts; ignore attached/forwarded reports.
        if (message.get_content_type() == "multipart/report"
                and message.get_param("report-type") == "delivery-status"):
            actions = []
            for part in message.iter_parts():
                if part.get_content_type() == "message/delivery-status":
                    for block in part.get_payload():
                        action = block.get("Action")
                        if action:
                            actions.append(str(action).strip().lower())
            headers["delivery_status_actions"] = ",".join(actions)
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
