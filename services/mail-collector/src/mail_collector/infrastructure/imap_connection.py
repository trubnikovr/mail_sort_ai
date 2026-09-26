import imaplib
import ssl

from mail_collector.mailboxes.models import MailboxAccount
from mail_collector.infrastructure.settings import Settings


class ImapConnectionFactory:
    """Creates a fresh TLS IMAP session with the configured app password."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def __call__(self, _: MailboxAccount) -> imaplib.IMAP4:
        session = imaplib.IMAP4_SSL(
            host=self._settings.imap_host or "",
            port=self._settings.imap_port,
            ssl_context=ssl.create_default_context(),
        )
        status, _ = session.login(
            self._settings.imap_username or "",
            self._settings.imap_app_password or "",
        )
        if status != "OK":
            session.logout()
            raise RuntimeError("IMAP authentication failed")
        return session
