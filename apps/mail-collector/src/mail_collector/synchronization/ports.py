from abc import ABC, abstractmethod

from mail_sort_contracts import ClassifyEmailJob

from mail_collector.mailboxes.models import MailboxAccount
from mail_collector.mailboxes.models import DiscoveredMessage


class EmailJobPublisherPort(ABC):
    @abstractmethod
    def publish(self, job: ClassifyEmailJob) -> None:
        raise NotImplementedError


class EmailRecordStorePort(ABC):
    @abstractmethod
    def upsert(self, account: MailboxAccount, message: DiscoveredMessage) -> str:
        raise NotImplementedError

    @abstractmethod
    def delete_expired(self) -> int:
        raise NotImplementedError
