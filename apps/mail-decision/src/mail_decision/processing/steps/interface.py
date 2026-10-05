from abc import ABC, abstractmethod

from mail_decision.processing.context import ProcessingContext


class ProcessingStep(ABC):
    """Interface for a step that reads and updates the workflow context."""

    @abstractmethod
    def execute(self, context: ProcessingContext) -> None:
        raise NotImplementedError
