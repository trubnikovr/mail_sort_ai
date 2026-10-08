import logging
from time import perf_counter

from exchangelib import Account, Configuration, Credentials, DELEGATE, Folder, NTLM
from exchangelib.errors import ErrorFolderNotFound

from mail_router.routing.registry import DestinationMailboxLookup, MailboxAction
from mail_router.routing.tasks import ClaimedRouteJob


logger = logging.getLogger(__name__)


class EwsMoveToFolderAction(MailboxAction):
    def __init__(
        self,
        endpoint: str,
        username: str,
        password: str,
        source_mailbox: str,
        destinations: DestinationMailboxLookup,
    ) -> None:
        self._credentials = Credentials(username=username, password=password)
        self._endpoint, self._source_mailbox, self._destinations = endpoint, source_mailbox, destinations

    def move_to_folder(self, job: ClaimedRouteJob) -> None:
        started = perf_counter()
        # The EWS login is also the primary SMTP address for this on-prem account.
        # ``account_id`` is an internal application identifier and must not be
        # passed to exchangelib as the mailbox address.
        logger.info("EWS client initialization: job_id=%s", job.id)
        account = Account(self._credentials.username, config=Configuration(service_endpoint=self._endpoint, credentials=self._credentials, auth_type=NTLM), autodiscover=False, access_type=DELEGATE)
        logger.info("resolving destination in database: job_id=%s destination_id=%s", job.id, job.destination_id)
        target = self._destinations.mailbox_for(job.account_id, job.destination_id)
        logger.info("EWS connecting and resolving target folder: job_id=%s target=%r", job.id, target)
        destination_parts = [part.strip() for part in target.strip("/").split("/") if part.strip()]
        destination = account.root
        if destination_parts and destination_parts[0].casefold() == "inbox":
            destination = account.inbox
            destination_parts = destination_parts[1:]
        for part in destination_parts:
            try:
                destination = destination / part
            except ErrorFolderNotFound:
                logger.info(
                    "EWS destination folder missing; creating: job_id=%s folder=%r",
                    job.id,
                    part,
                )
                destination = Folder(parent=destination, name=part).save()
        logger.info("EWS target folder ready: job_id=%s target=%r", job.id, target)
        logger.info("EWS resolving source folder: job_id=%s source=%r", job.id, self._source_mailbox)
        if self._source_mailbox.strip().lower() == "inbox":
            source = account.inbox
        else:
            source = account.root
            for part in self._source_mailbox.strip("/").split("/"):
                if part:
                    source = source / part
        logger.info("EWS source folder found; fetching message by stored ID: job_id=%s", job.id)
        item = source.get(id=job.provider_message_id)
        logger.info("EWS message found; moving: job_id=%s source=%r target=%r", job.id, self._source_mailbox, target)
        item.move(to_folder=destination)
        logger.info("EWS move confirmed: job_id=%s target=%r duration_seconds=%.2f", job.id, target, perf_counter() - started)
