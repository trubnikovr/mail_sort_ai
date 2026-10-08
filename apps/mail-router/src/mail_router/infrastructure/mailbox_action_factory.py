from collections.abc import Callable

from mail_sort_contracts import MailProvider

from mail_router.routing.registry import MailboxAction, MailboxConnectionLookup, DestinationMailboxLookup
from .ews_mailbox import EwsMoveToFolderAction
from .imap_mailbox import ImapMoveToFolderAction


class MailboxActionFactory:
    """Build provider-specific actions that resolve credentials per job account."""

    def __init__(self, accounts: MailboxConnectionLookup, destinations: DestinationMailboxLookup) -> None:
        self._builders: dict[MailProvider, Callable[[], MailboxAction]] = {
            "imap": lambda: ImapMoveToFolderAction(accounts, destinations),
            "ews": lambda: EwsMoveToFolderAction(accounts, destinations),
        }

    def resolve(self, provider: MailProvider) -> MailboxAction:
        try:
            return self._builders[provider]()
        except KeyError as error:
            raise ValueError(f"Unsupported mailbox provider: {provider}") from error
