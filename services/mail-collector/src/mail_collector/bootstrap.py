from mail_sort_database import create_session_factory

from .infrastructure.mailbox_source_factory import MailboxSourceFactory
from .infrastructure.persistence import (
    EmailJobPublisher,
    EmailRecordStore,
)
from .mailboxes.registry import MailboxSourceRegistry
from .infrastructure.settings import Settings
from .synchronization.service import MailboxSynchronizationService


def build_synchronization_service(settings: Settings) -> MailboxSynchronizationService:
    """Wire collector ports to their IMAP and PostgreSQL implementations."""
    sessions = create_session_factory(settings.database_url)
    source_factory = MailboxSourceFactory(settings)
    mail_sources = [
        (settings.mailbox_provider, source_factory.resolve(settings.mailbox_provider)),
    ]
    return MailboxSynchronizationService(
        mail_sources=MailboxSourceRegistry(mail_sources),
        job_publisher=EmailJobPublisher(sessions),
        email_records=EmailRecordStore(sessions),
    )
