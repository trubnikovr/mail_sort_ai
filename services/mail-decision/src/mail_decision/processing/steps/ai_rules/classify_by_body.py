import logging

from mail_decision.classification.service import ClassificationService
from mail_decision.processing.context import (
    DailyRequestLimitReached,
    REVIEW_DESTINATION_ID,
    ProcessingContext,
    ProcessingOutcome,
)

from ..interface import ProcessingStep


logger = logging.getLogger(__name__)


class ClassifyByBody(ProcessingStep):
    def __init__(
        self,
        classifier: ClassificationService,
        confidence_threshold: float,
    ) -> None:
        self._classifier = classifier
        self._confidence_threshold = confidence_threshold

    def execute(self, context: ProcessingContext) -> None:
        if context.prepared_email is None:
            raise RuntimeError("Email must be prepared before body classification")
        email = context.prepared_email
        logger.info(
            "AI body request started: job_id=%s body_characters=%s destinations=%s",
            context.job.id, len(email.body), len(context.destinations),
        )
        try:
            response = self._classifier.classify_body(
                email.sender,
                email.subject,
                email.body,
                context.destinations,
            )
        except DailyRequestLimitReached:
            raise
        except Exception as error:
            logger.error(
                "AI classification failed; routing to review: job_id=%s error_type=%s",
                context.job.id,
                type(error).__name__,
            )
            if REVIEW_DESTINATION_ID not in context.destinations:
                raise RuntimeError("Manual review destination is not configured") from None
            context.outcome = ProcessingOutcome(
                status="review",
                destination_id=REVIEW_DESTINATION_ID,
                source="ai_body",
                confidence=None,
                reason=f"AI classification failed ({type(error).__name__})",
            )
            return
        if response.action == "review":
            if REVIEW_DESTINATION_ID not in context.destinations:
                raise RuntimeError("Manual review destination is not configured")
            context.outcome = ProcessingOutcome(
                status="review",
                destination_id=REVIEW_DESTINATION_ID,
                source="ai_body", confidence=response.confidence, reason=response.reason,
            )
            return
        if response.action != "classified":
            raise ValueError("AI requested the email body after the body was already provided")
        if response.destination_id not in context.destinations:
            raise ValueError("AI returned a destination outside the allowed list")
        confidence = response.confidence if response.confidence is not None else 0
        needs_review = confidence < self._confidence_threshold
        logger.info(
            "AI body result: job_id=%s suggested_destination_id=%s confidence=%.3f threshold=%.3f needs_review=%s",
            context.job.id, response.destination_id, confidence, self._confidence_threshold, needs_review,
        )
        destination_id = REVIEW_DESTINATION_ID if needs_review else response.destination_id
        if needs_review and destination_id not in context.destinations:
            raise RuntimeError("Manual review destination is not configured")
        context.outcome = ProcessingOutcome(
            status="review" if needs_review else "completed",
            destination_id=destination_id,
            source="ai_body",
            confidence=confidence,
            reason=response.reason,
        )
