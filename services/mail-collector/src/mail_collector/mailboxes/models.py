from dataclasses import dataclass
from datetime import datetime

from mail_sort_contracts import MailProvider


@dataclass(frozen=True, slots=True)
class MailboxAccount:
    id: str
    provider: MailProvider
    mailbox: str = "INBOX"


@dataclass(frozen=True, slots=True)
class DiscoveredMessage:
    provider_message_id: str
    headers: dict[str, str]
    body: str
    received_at: datetime | None


@dataclass(frozen=True, slots=True)
class SyncPage:
    messages: tuple[DiscoveredMessage, ...]
    next_cursor: str


class CursorExpiredError(RuntimeError):
    """The provider can no longer incrementally sync from this cursor."""
