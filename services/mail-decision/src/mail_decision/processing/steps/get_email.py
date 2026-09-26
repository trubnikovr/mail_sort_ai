from mail_decision.processing.context import ProcessingContext
from mail_decision.processing.ports import EmailReader

from .interface import ProcessingStep


class GetEmail(ProcessingStep):
    def __init__(self, reader: EmailReader) -> None:
        self._reader = reader

    def execute(self, context: ProcessingContext) -> None:
        context.email = self._reader.read(context.job)
