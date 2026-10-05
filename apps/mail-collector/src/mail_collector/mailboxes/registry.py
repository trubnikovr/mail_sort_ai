from collections.abc import Iterable

from mail_sort_contracts import MailProvider

from .models import MailboxAccount
from .port import MailboxSource


class MailboxSourceRegistry:
    """Resolves the configured source without leaking providers into synchronization."""

    def __init__(self, sources: Iterable[tuple[MailProvider, MailboxSource]]) -> None:
        self._sources = dict(sources)

    def for_account(self, account: MailboxAccount) -> MailboxSource:
        try:
            return self._sources[account.provider]
        except KeyError as error:
            raise ValueError(f"Unsupported mailbox provider: {account.provider}") from error
