import imaplib
import logging
from time import perf_counter

from mail_router.routing.registry import DestinationMailboxLookup, MailboxAction, MailboxConnectionLookup
from mail_router.routing.tasks import ClaimedRouteJob


logger = logging.getLogger(__name__)


class ImapMoveToFolderAction(MailboxAction):
    """Moves an IMAP UID from the source mailbox into the configured destination."""

    def __init__(
        self,
        accounts: MailboxConnectionLookup,
        destinations: DestinationMailboxLookup,
    ) -> None:
        self._accounts = accounts
        self._destinations = destinations

    def move_to_folder(self, job: ClaimedRouteJob) -> None:
        started = perf_counter()
        mailbox = self._accounts.connection_for(job.account_id)
        if mailbox.provider != "imap":
            raise ValueError(f"Mailbox account {job.account_id!r} is not configured for IMAP")
        logger.info("resolving destination in database: job_id=%s destination_id=%s", job.id, job.destination_id)
        target_mailbox = self._destinations.mailbox_for(job.account_id, job.destination_id)
        logger.info("IMAP connecting: job_id=%s target=%r", job.id, target_mailbox)
        session = imaplib.IMAP4_SSL(mailbox.host, mailbox.port)
        try:
            logger.info("IMAP authenticating: job_id=%s", job.id)
            session.login(mailbox.username, mailbox.password)
            logger.info("IMAP authenticated; selecting source folder: job_id=%s source=%r", job.id, mailbox.source_mailbox)
            status, _ = session.select(mailbox.source_mailbox, readonly=False)
            if status != "OK":
                raise RuntimeError(f"Cannot select {mailbox.source_mailbox!r}")
            target = target_mailbox.replace("\\", "\\\\").replace('"', '\\"')
            logger.info("IMAP moving message by stored UID: job_id=%s source=%r target=%r", job.id, mailbox.source_mailbox, target_mailbox)
            status, _ = session.uid(
                "MOVE",
                job.provider_message_id,
                f'"{target}"',
            )
            if status != "OK":
                raise RuntimeError(f"Cannot move email to IMAP mailbox {target_mailbox!r}")
            logger.info("IMAP move confirmed: job_id=%s target=%r duration_seconds=%.2f", job.id, target_mailbox, perf_counter() - started)
        finally:
            logger.info("IMAP disconnecting: job_id=%s", job.id)
            try:
                session.logout()
            except imaplib.IMAP4.error:
                pass
