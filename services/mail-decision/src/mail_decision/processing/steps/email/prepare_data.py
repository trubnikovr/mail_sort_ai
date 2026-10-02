from mail_decision.processing.context import EmailContent, ProcessingContext

from ..interface import ProcessingStep


class PrepareData(ProcessingStep):
    """Normalizes collector data and bounds the payload that can reach the AI."""

    def __init__(self, max_body_characters: int) -> None:
        self._max_body_characters = max_body_characters

    def execute(self, context: ProcessingContext) -> None:
        email = context.email
        if email is None:
            raise RuntimeError("Email must be loaded before preparing data")
        prepared = EmailContent(
            headers=email.headers,
            sender=email.sender.strip(),
            subject=email.subject.strip(),
            body=email.body.strip()[: self._max_body_characters],
        )
        if not prepared.sender and not prepared.subject and not prepared.body:
            raise ValueError("Email has no sender, subject, or body to classify")
        context.prepared_email = prepared
