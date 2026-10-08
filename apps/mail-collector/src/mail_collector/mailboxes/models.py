from dataclasses import dataclass, field
from datetime import datetime

from mail_sort_contracts import MailProvider


@dataclass(frozen=True, slots=True)
class MailboxAccount:
    id: str
    provider: MailProvider
    mailbox: str = "INBOX"
    email_address: str = ""
    host: str = ""
    port: int = 993
    username: str = ""
    password: str = field(default="", repr=False)


@dataclass(frozen=True, slots=True)
class DiscoveredMessage:
    provider_message_id: str
    headers: dict[str, str]
    body: str
    received_at: datetime | None


@dataclass(frozen=True, slots=True)
class SyncPage:
    messages: tuple[DiscoveredMessage, ...]
