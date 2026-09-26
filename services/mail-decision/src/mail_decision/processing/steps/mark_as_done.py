from mail_decision.processing.context import ProcessingContext
from mail_decision.processing.ports import ClassificationResultStore

from .interface import ProcessingStep


class MarkAsDone(ProcessingStep):
    """Persist a decision and atomically enqueue its mailbox action."""

    def __init__(self, results: ClassificationResultStore) -> None:
        self._results = results

    def execute(self, context: ProcessingContext) -> None:
        if context.outcome is None:
            raise RuntimeError("Classification outcome must exist before finalizing")
        self._results.finalize(context.job, context.outcome)
