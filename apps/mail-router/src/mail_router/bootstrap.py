from mail_sort_database.session import create_session_factory

from .infrastructure.mailbox_action_factory import MailboxActionFactory
from .infrastructure.persistence import DestinationRepository, MailboxAccountRepository, RouteJobStore
from .routing.registry import MailboxActionRegistry
from .routing.worker import MailboxActionWorker
from .infrastructure.settings import Settings


def build_worker(settings: Settings) -> MailboxActionWorker:
    sessions = create_session_factory(settings.database_url)
    destinations = DestinationRepository(sessions)
    accounts = MailboxAccountRepository(sessions)
    factory = MailboxActionFactory(accounts, destinations)
    actions = [(provider, factory.resolve(provider)) for provider in ("imap", "ews")]
    return MailboxActionWorker(
        actions=MailboxActionRegistry(actions),
        jobs=RouteJobStore(sessions, settings.worker_id),
        retry_delay_seconds=settings.retry_delay_seconds,
        stale_job_timeout_seconds=settings.stale_job_timeout_seconds,
    )
