from mail_decision.processing.context import ProcessingContext, ProcessingOutcome
from mail_decision.processing.ports import DestinationRepository

from ..interface import ProcessingStep


class DetectNdr(ProcessingStep):
    """Resolve explicit provider delivery-failure reports before spending AI quota."""

    def __init__(self, destinations: DestinationRepository) -> None:
        self._destinations = destinations

    def execute(self, context: ProcessingContext) -> None:
        if context.email is None:
            raise RuntimeError("Email must be loaded before detecting NDR")
        headers = context.email.headers
        item_class = headers.get("item_class", "").strip().upper()
        actions = headers.get("delivery_status_actions", "").split(",")
        is_ndr = (
            item_class.startswith("REPORT.") and item_class.endswith(".NDR")
        ) or "failed" in {action.strip().lower() for action in actions}
        if not is_ndr:
            return
        destinations = self._destinations.active_for_account(context.job.account_id)
        if "ndr" not in destinations:
            raise ValueError("Active NDR destination 'ndr' is not configured")
        context.outcome = ProcessingOutcome(
            status="completed",
            destination_id="ndr",
            source="ndr_rule",
            confidence=None,
            reason="Provider delivery-failure report",
        )
