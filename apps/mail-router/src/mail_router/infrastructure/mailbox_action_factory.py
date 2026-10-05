from .ews_mailbox import EwsMoveToFolderAction
from .imap_mailbox import ImapMoveToFolderAction
from .persistence import DestinationRepository
from .settings import Settings


class MailboxActionFactory:
    """Builds the provider adapter selected by configuration."""

    def __init__(self, settings: Settings, destinations: DestinationRepository) -> None:
        self._settings = settings
        self._destinations = destinations

    def resolve(self):
        if self._settings.mailbox_provider == "imap":
            return ImapMoveToFolderAction(
                host=self._settings.imap_host or "",
                port=self._settings.imap_port,
                username=self._settings.imap_username or "",
                app_password=self._settings.imap_app_password or "",
                source_mailbox=self._settings.mailbox_source,
                destinations=self._destinations,
            )
        return EwsMoveToFolderAction(
            endpoint=self._settings.ews_endpoint or "",
            username=self._settings.ews_username or "",
            password=self._settings.ews_password or "",
            source_mailbox=self._settings.mailbox_source,
            destinations=self._destinations,
        )
