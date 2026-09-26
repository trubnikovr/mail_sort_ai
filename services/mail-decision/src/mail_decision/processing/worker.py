import logging
from abc import ABC, abstractmethod
from time import sleep

from .context import ClaimedEmailJob, DailyRequestLimitReached
from .email_classification_process import EmailClassificationProcess


class JobClaimer(ABC):
    @abstractmethod
    def recover_stale(self, timeout_seconds: int) -> int:
        raise NotImplementedError

    @abstractmethod
    def claim_next(self) -> ClaimedEmailJob | None:
        raise NotImplementedError

    @abstractmethod
    def retry(self, job_id: str, error: Exception, retry_delay_seconds: int) -> None:
        raise NotImplementedError


class JobWorker:
    """Runs one claimed database job at a time."""

    def __init__(
        self,
        process: EmailClassificationProcess,
        jobs: JobClaimer,
        retry_delay_seconds: int,
        stale_job_timeout_seconds: int,
    ) -> None:
        self._process = process
        self._jobs = jobs
        self._retry_delay_seconds = retry_delay_seconds
        self._stale_job_timeout_seconds = stale_job_timeout_seconds
        self._logger = logging.getLogger(__name__)

    def run_once(self) -> bool:
        recovered = self._jobs.recover_stale(self._stale_job_timeout_seconds)
        if recovered:
            self._logger.info("recovered stale classification jobs: count=%s", recovered)
        job = self._jobs.claim_next()
        if job is None:
            self._logger.info("no eligible classification jobs in queue")
            return False
        self._logger.info("claimed classification job: job_id=%s", job.id)
        try:
            self._process.execute(job)
        except Exception as error:
            retry_delay = (
                error.retry_delay_seconds()
                if isinstance(error, DailyRequestLimitReached)
                else self._retry_delay_seconds
            )
            self._jobs.retry(job.id, error, retry_delay)
            self._logger.exception("mail processing failed: job_id=%s", job.id)
        else:
            self._logger.info("classification job processed: job_id=%s", job.id)
        return True

    def run_forever(self, poll_interval_seconds: int) -> None:
        self._logger.info(
            "decision worker started: poll_interval_seconds=%s",
            poll_interval_seconds,
        )
        while True:
            if not self.run_once():
                self._logger.info(
                    "checking classification queue again in %s seconds",
                    poll_interval_seconds,
                )
                sleep(poll_interval_seconds)
