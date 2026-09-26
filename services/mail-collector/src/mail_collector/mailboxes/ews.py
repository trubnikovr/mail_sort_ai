from datetime import UTC, datetime

from exchangelib import Account, Configuration, Credentials, DELEGATE, NTLM

from .models import DiscoveredMessage, MailboxAccount, SyncPage
from .port import MailboxSource


class EwsMailboxSource(MailboxSource):
    """On-premises EWS source backed by exchangelib and NTLM."""

    def __init__(self, endpoint: str, username: str, password: str) -> None:
        self._endpoint = endpoint
        self._credentials = Credentials(username=username, password=password)

    def collect(self, account: MailboxAccount, cursor: str | None) -> SyncPage:
        mailbox = Account(
            primary_smtp_address=self._credentials.username,
            config=Configuration(
                service_endpoint=self._endpoint,
                credentials=self._credentials,
                auth_type=NTLM,
            ),
            autodiscover=False,
            access_type=DELEGATE,
        )
        folder = self._folder(mailbox, account.mailbox)
        items = folder.all().order_by("datetime_received")
        if cursor:
            items = items.filter(datetime_received__gt=datetime.fromisoformat(cursor))
        messages = tuple(self._message(item) for item in items[:50])
        next_cursor = messages[-1].received_at.isoformat() if messages and messages[-1].received_at else (cursor or "")
        return SyncPage(messages=messages, next_cursor=next_cursor)

    @staticmethod
    def _folder(mailbox: Account, path: str):
        if path.strip().lower() == "inbox":
            return mailbox.inbox
        folder = mailbox.root
        for part in path.strip("/").split("/"):
            if part:
                folder = folder / part
        return folder

    @staticmethod
    def _message(item: object) -> DiscoveredMessage:
        received = getattr(item, "datetime_received", None)
        if received and received.tzinfo is None:
            received = received.replace(tzinfo=UTC)
        sender = getattr(getattr(item, "sender", None), "email_address", "") or ""
        return DiscoveredMessage(
            provider_message_id=getattr(item, "id"),
            headers={"from": sender, "subject": getattr(item, "subject", "") or ""},
            body=str(getattr(item, "text_body", "") or "").strip(),
            received_at=received,
        )
