import logging

from mail_decision.processing.context import DailyRequestLimitReached, ProcessingContext
from mail_decision.processing.ports import AiRequestQuota

from ..interface import ProcessingStep

logger = logging.getLogger(__name__)


class AcquireAiRequestPermit(ProcessingStep):
    """Atomically consume one daily permit immediately before an AI call."""

    def __init__(self, quota: AiRequestQuota, provider: str) -> None:
        self._quota = quota
        self._provider = provider

    def execute(self, context: ProcessingContext) -> None:
        if not self._quota.acquire(self._provider):
            raise DailyRequestLimitReached("Daily AI request limit reached")
        logger.info("AI request permit acquired: job_id=%s provider=%s",
                    context.job.id, self._provider)
