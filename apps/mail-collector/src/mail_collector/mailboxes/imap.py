from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
import imaplib
import ssl

from .models import DiscoveredMessage, MailboxAccount, SyncPage
from .port import MailboxSource


class ImapMailboxSource(MailboxSource):
    """Reads unread messages from the configured IMAP folder."""

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password

    def collect(self, account: MailboxAccount) -> SyncPage:
        session = imaplib.IMAP4_SSL(
            host=self._host,
            port=self._port,
            ssl_context=ssl.create_default_context(),
        )
        status, _ = session.login(self._username, self._password)
        if status != "OK":
            session.logout()
            raise RuntimeError("IMAP authentication failed")
        try:
            status, _ = session.select(account.mailbox, readonly=True)
            if status != "OK":
                raise RuntimeError(f"Could not select IMAP mailbox {account.mailbox!r}")
            status, data = session.uid("SEARCH", None, "UNSEEN")
            if status != "OK":
                raise RuntimeError("IMAP UID SEARCH failed")
            uids = [int(value) for value in data[0].split()] if data and data[0] else []
            messages = tuple(self._read_message(session, uid) for uid in uids)
        finally:
            session.logout()

        return SyncPage(messages=messages)

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
            body=ImapMailboxSource._extract_body(message),
            received_at=ImapMailboxSource._received_at(message),
        )

    @staticmethod
    def _extract_body(message: object) -> str:
        from email.message import Message

        if not isinstance(message, Message):
            return ""
        if not message.is_multipart():
            return ImapMailboxSource._decode_part(message)

        plain_parts: list[str] = []
        html_parts: list[str] = []
        for part in message.walk():
            if part.is_multipart() or part.get_content_disposition() == "attachment":
                continue
            content_type = part.get_content_type()
            if content_type not in {"text/plain", "text/html"}:
                continue
            decoded = ImapMailboxSource._decode_part(part)
            if decoded:
                (plain_parts if content_type == "text/plain" else html_parts).append(decoded)

        if plain_parts:
            return "\n".join(plain_parts).strip()
        if html_parts:
            from html import unescape
            from html.parser import HTMLParser

            class _TextExtractor(HTMLParser):
                def __init__(self) -> None:
                    super().__init__()
                    self.parts: list[str] = []

                def handle_data(self, data: str) -> None:
                    self.parts.append(data)

            parser = _TextExtractor()
            parser.feed("\n".join(html_parts))
            return unescape(" ".join(parser.parts)).strip()
        return ""

    @staticmethod
    def _decode_part(part: object) -> str:
        from email.message import Message

        if not isinstance(part, Message):
            return ""
        try:
            content = part.get_content()
        except (LookupError, UnicodeDecodeError, AttributeError):
            payload = part.get_payload(decode=True)
            if not payload:
                return ""
            charset = part.get_content_charset() or "utf-8"
            try:
                content = payload.decode(charset, errors="replace")
            except LookupError:
                content = payload.decode("utf-8", errors="replace")
        return content.strip() if isinstance(content, str) else ""

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
