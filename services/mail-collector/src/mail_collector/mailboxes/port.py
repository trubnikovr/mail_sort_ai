from abc import ABC, abstractmethod

from .models import MailboxAccount, SyncPage


class MailboxSource(ABC):
    """Provider-specific source of mailbox messages."""

    @abstractmethod
    def collect(self, account: MailboxAccount) -> SyncPage:
        raise NotImplementedError
