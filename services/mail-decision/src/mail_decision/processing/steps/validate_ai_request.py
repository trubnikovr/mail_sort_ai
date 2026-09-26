import logging

from mail_decision.processing.ports import AiRequestQuota, DestinationRepository
from mail_decision.processing.context import DailyRequestLimitReached, ProcessingContext

from .interface import ProcessingStep


logger = logging.getLogger(__name__)


class ValidateAiRequest(ProcessingStep):
    """Checks preconditions and reserves quota before one AI request."""

    def __init__(
        self,
        destinations: DestinationRepository,
        quota: AiRequestQuota,
        provider: str,
    ) -> None:
        self._destinations = destinations
        self._quota = quota
        self._provider = provider

    def execute(self, context: ProcessingContext) -> None:
        if context.outcome is not None:
            logger.info("AI request validation skipped: job_id=%s decision already available", context.job.id)
            return
        destinations = self._destinations.active_for_account(context.job.account_id)
        if not destinations:
            raise ValueError("No active destinations configured for this mailbox")
        if not self._quota.reserve(self._provider):
            raise DailyRequestLimitReached("Daily AI request limit reached")
        context.destinations = destinations
        logger.info(
            "AI request allowed: job_id=%s provider=%s active_destinations=%s quota_reserved=true",
            context.job.id, self._provider, len(destinations),
        )
