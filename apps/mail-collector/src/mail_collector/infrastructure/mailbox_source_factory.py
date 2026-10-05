from collections.abc import Callable

from mail_sort_contracts import MailProvider

from mail_collector.mailboxes.ews import EwsMailboxSource
from mail_collector.mailboxes.imap import ImapMailboxSource
from mail_collector.mailboxes.port import MailboxSource
from mail_collector.infrastructure.settings import Settings


class MailboxSourceFactory:
    """Builds the source adapter selected by the configured mailbox provider."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._builders: dict[MailProvider, Callable[[], MailboxSource]] = {
            "imap": self._build_imap,
            "ews": self._build_ews,
        }

    def resolve(self, provider: MailProvider) -> MailboxSource:
        try:
            return self._builders[provider]()
        except KeyError as error:
            raise ValueError(f"Unsupported mailbox provider: {provider}") from error

    def _build_imap(self) -> ImapMailboxSource:
        return ImapMailboxSource(
            host=self._settings.imap_host or "",
            port=self._settings.imap_port,
            username=self._settings.imap_username or "",
            password=self._settings.imap_app_password or "",
        )

    def _build_ews(self) -> EwsMailboxSource:
        return EwsMailboxSource(
            endpoint=self._settings.ews_endpoint or "",
            username=self._settings.ews_username or "",
            password=self._settings.ews_password or "",
        )
