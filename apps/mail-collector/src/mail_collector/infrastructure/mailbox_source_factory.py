from collections.abc import Callable

from mail_sort_contracts import MailProvider

from mail_collector.mailboxes.ews import EwsMailboxSource
from mail_collector.mailboxes.imap import ImapMailboxSource
from mail_collector.mailboxes.port import MailboxSource


class MailboxSourceFactory:
    """Builds the source adapter selected by the configured mailbox provider."""

    def __init__(self) -> None:
        self._builders: dict[MailProvider, Callable[[], MailboxSource]] = {
            "imap": ImapMailboxSource,
            "ews": EwsMailboxSource,
        }

    def resolve(self, provider: MailProvider) -> MailboxSource:
        try:
            return self._builders[provider]()
        except KeyError as error:
            raise ValueError(f"Unsupported mailbox provider: {provider}") from error
