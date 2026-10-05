import logging
from abc import ABC, abstractmethod
from time import perf_counter, sleep

from mail_sort_logging import log_context

from .registry import MailboxActionRegistry
from .tasks import ClaimedRouteJob


class MailboxActionClaimer(ABC):
    @abstractmethod
    def recover_stale(self, timeout_seconds: int) -> int:
        raise NotImplementedError

    @abstractmethod
    def claim_next(self) -> ClaimedRouteJob | None:
        raise NotImplementedError

    @abstractmethod
    def complete(self, job_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def retry(self, job_id: str, error: Exception, retry_delay_seconds: int) -> None:
        raise NotImplementedError


class MailboxActionWorker:
    """Executes durable route_email jobs through the selected provider adapter."""

    def __init__(
        self,
        actions: MailboxActionRegistry,
        jobs: MailboxActionClaimer,
        retry_delay_seconds: int,
        stale_job_timeout_seconds: int,
    ) -> None:
        self._actions = actions
        self._jobs = jobs
        self._retry_delay_seconds = retry_delay_seconds
        self._stale_job_timeout_seconds = stale_job_timeout_seconds
        self._logger = logging.getLogger(__name__)

    def run_once(self) -> bool:
        self._logger.info("checking stale route jobs: timeout_seconds=%s", self._stale_job_timeout_seconds)
        recovered = self._jobs.recover_stale(self._stale_job_timeout_seconds)
        self._logger.info("stale route jobs recovered: count=%s", recovered)
        self._logger.info("checking route queue for an eligible job")
        job = self._jobs.claim_next()
        if job is None:
            self._logger.info("no eligible route jobs: require pending status, retry_at reached and remaining attempts")
            return False
        started = perf_counter()
        with log_context(
            job_id=job.id,
            account_id=job.account_id,
            provider=job.provider,
            provider_message_id=job.provider_message_id,
            subject=job.subject,
        ):
            self._logger.info("route job claimed: destination_id=%s", job.destination_id)
            phase = "mailbox_move"
            try:
                self._actions.move(job)
                phase = "save_completed_status"
                self._logger.info("mailbox move confirmed; saving completed status")
                self._jobs.complete(job.id)
            except Exception as error:
                self._logger.exception("route job failed: phase=%s duration_seconds=%.2f", phase, perf_counter() - started)
                self._logger.info("saving route failure and retry decision")
                self._jobs.retry(job.id, error, self._retry_delay_seconds)
            else:
                self._logger.info("route job completed: destination_id=%s duration_seconds=%.2f", job.destination_id, perf_counter() - started)
        return True

    def run_forever(self, poll_interval_seconds: int) -> None:
        self._logger.info(
            "router worker started: poll_interval_seconds=%s", poll_interval_seconds,
        )
        while True:
            if not self.run_once():
                self._logger.info(
                    "checking route queue again in %s seconds", poll_interval_seconds,
                )
                sleep(poll_interval_seconds)
