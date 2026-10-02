import logging

from mail_decision.classification.service import ClassificationService
from mail_decision.processing.context import REVIEW_DESTINATION_ID, ProcessingContext, ProcessingOutcome

from ..interface import ProcessingStep


logger = logging.getLogger(__name__)


class ClassifyBySubject(ProcessingStep):
    def __init__(
        self,
        classifier: ClassificationService,
        confidence_threshold: float,
    ) -> None:
        self._classifier = classifier
        self._confidence_threshold = confidence_threshold

    def execute(self, context: ProcessingContext) -> None:
        if context.prepared_email is None:
            raise RuntimeError("Email must be prepared before subject classification")
        email = context.prepared_email
        logger.info("AI subject request started: job_id=%s destinations=%s", context.job.id, len(context.destinations))
        response = self._classifier.classify_subject(
            email.sender,
            email.subject,
            context.destinations,
        )
        if response.action == "need_body":
            logger.info("AI subject result: job_id=%s action=need_body; continuing with body", context.job.id)
            return
        if response.action == "review":
            if REVIEW_DESTINATION_ID not in context.destinations:
                raise RuntimeError("Manual review destination is not configured")
            context.outcome = ProcessingOutcome(
                status="review",
                destination_id=REVIEW_DESTINATION_ID,
                source="ai_subject",
                confidence=response.confidence,
                reason=response.reason,
            )
            return
        if response.destination_id not in context.destinations:
            raise ValueError("AI returned a destination outside the allowed list")
        confidence = response.confidence if response.confidence is not None else 0
        logger.info(
            "AI subject result: job_id=%s destination_id=%s confidence=%.3f threshold=%.3f next=%s",
            context.job.id, response.destination_id, confidence, self._confidence_threshold,
            "body_classification" if confidence < self._confidence_threshold else "save_result",
        )
        if confidence < self._confidence_threshold:
            if REVIEW_DESTINATION_ID not in context.destinations:
                raise RuntimeError("Manual review destination is not configured")
            context.outcome = ProcessingOutcome(
                status="review",
                destination_id=REVIEW_DESTINATION_ID,
                source="ai_subject",
                confidence=confidence,
                reason=response.reason,
            )
            return
        context.outcome = ProcessingOutcome(
            status="completed",
            destination_id=response.destination_id or "",
            source="ai_subject",
            confidence=confidence,
            reason=response.reason,
        )
