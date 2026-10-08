from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ClaimedRouteJob:
    id: str
    account_id: str
    provider: str
    provider_message_id: str
    action: str
    destination_id: str
    subject: str = ""


@dataclass(frozen=True, slots=True)
class MailboxConnection:
    id: str
    provider: str
    email_address: str
    source_mailbox: str
    host: str
    port: int
    username: str
    password: str = field(repr=False)
