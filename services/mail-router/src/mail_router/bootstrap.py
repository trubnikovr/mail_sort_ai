from mail_sort_database.session import create_session_factory

from .infrastructure.mailbox_action_factory import MailboxActionFactory
from .infrastructure.persistence import DestinationRepository, RouteJobStore
from .routing.registry import MailboxActionRegistry
from .routing.worker import MailboxActionWorker
from .infrastructure.settings import Settings


def build_worker(settings: Settings) -> MailboxActionWorker:
    sessions = create_session_factory(settings.database_url)
    destinations = DestinationRepository(settings.mailbox_account_id)
    actions = [(settings.mailbox_provider, MailboxActionFactory(settings, destinations).resolve())]
    return MailboxActionWorker(
        actions=MailboxActionRegistry(actions),
        jobs=RouteJobStore(sessions, settings.worker_id),
        retry_delay_seconds=settings.retry_delay_seconds,
        stale_job_timeout_seconds=settings.stale_job_timeout_seconds,
    )
