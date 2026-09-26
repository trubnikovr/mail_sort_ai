from abc import ABC, abstractmethod
from collections.abc import Iterable

from mail_sort_contracts import MailProvider

from .tasks import ClaimedRouteJob


class MailboxAction(ABC):
    @abstractmethod
    def move_to_folder(self, job: ClaimedRouteJob) -> None:
        raise NotImplementedError


class DestinationMailboxLookup(ABC):
    @abstractmethod
    def mailbox_for(self, account_id: str, destination_id: str) -> str:
        raise NotImplementedError


class MailboxActionRegistry:
    """Resolves the mailbox action strategy without leaking providers into workers."""

    def __init__(self, actions: Iterable[tuple[MailProvider, MailboxAction]]) -> None:
        self._actions = dict(actions)

    def move(self, job: ClaimedRouteJob) -> None:
        try:
            action = self._actions[job.provider]
        except KeyError as error:
            raise ValueError(f"Unsupported mailbox provider: {job.provider}") from error
        action.move_to_folder(job)
