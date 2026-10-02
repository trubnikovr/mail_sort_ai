from abc import ABC, abstractmethod

from .context import ClaimedEmailJob, EmailContent, ProcessingOutcome


class EmailReader(ABC):
    @abstractmethod
    def read(self, job: ClaimedEmailJob) -> EmailContent:
        raise NotImplementedError


class DestinationRepository(ABC):
    @abstractmethod
    def active_for_account(self, account_id: str) -> dict[str, str]:
        raise NotImplementedError


class ClassificationResultStore(ABC):
    @abstractmethod
    def finalize(self, job: ClaimedEmailJob, outcome: ProcessingOutcome) -> None:
        raise NotImplementedError


class AiRequestQuota(ABC):
    @abstractmethod
    def acquire(self, provider: str) -> bool:
        raise NotImplementedError
