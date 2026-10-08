import logging

from mail_decision.processing.ports import DestinationRepository
from mail_decision.processing.context import ProcessingContext

from ..interface import ProcessingStep

logger = logging.getLogger(__name__)


class LoadDestinations(ProcessingStep):
    """Load the active destinations used by the remaining processing steps."""

    def __init__(self, destinations: DestinationRepository) -> None:
        self._destinations = destinations

    def execute(self, context: ProcessingContext) -> None:
        destinations = self._destinations.active_for_account(context.job.account_id)
        if not destinations:
            raise ValueError("No active destinations configured for this mailbox")
        context.destinations = destinations
        logger.info("AI request validated: job_id=%s active_destinations=%s",
                    context.job.id, len(destinations))
