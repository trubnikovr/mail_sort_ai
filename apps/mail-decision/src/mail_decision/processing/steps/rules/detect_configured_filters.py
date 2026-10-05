import logging

from mail_decision.processing.context import ProcessingContext, ProcessingOutcome

from ..interface import ProcessingStep


logger = logging.getLogger(__name__)


class DetectConfiguredFilters(ProcessingStep):
    """Apply deterministic mailbox filters before NDR handling and AI."""

    _SUBJECT_PREFIX_DESTINATIONS = (
        ("daily spam report for", "trash"),
    )

    def execute(self, context: ProcessingContext) -> None:
        if context.email is None:
            raise RuntimeError("Email must be loaded before applying configured filters")
        subject = context.email.subject.strip().casefold()
        for prefix, destination_id in self._SUBJECT_PREFIX_DESTINATIONS:
            if subject.startswith(prefix):
                context.outcome = ProcessingOutcome(
                    status="completed",
                    destination_id=destination_id,
                    source="subject_filter",
                    confidence=None,
                    reason=f"Subject matched configured prefix: {prefix}",
                )
                logger.info(
                    "configured subject filter matched: job_id=%s destination_id=%s",
                    context.job.id,
                    destination_id,
                )
                return
