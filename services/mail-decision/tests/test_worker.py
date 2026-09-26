import unittest

from mail_decision.processing.context import ClaimedEmailJob
from mail_decision.processing.worker import JobWorker


class _Process:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.jobs = []

    def execute(self, job: ClaimedEmailJob) -> None:
        self.jobs.append(job)
        if self.error:
            raise self.error


class _Jobs:
    def __init__(self, job: ClaimedEmailJob | None) -> None:
        self.job = job
        self.retries = []

    def claim_next(self) -> ClaimedEmailJob | None:
        job, self.job = self.job, None
        return job

    def recover_stale(self, _: int) -> int:
        return 0

    def retry(self, job_id: str, error: Exception, retry_delay_seconds: int) -> None:
        self.retries.append((job_id, str(error), retry_delay_seconds))


class WorkerTest(unittest.TestCase):
    def test_processes_one_claimed_job(self) -> None:
        job = ClaimedEmailJob("job-1", "account", "uid-1", "record-1")
        process = _Process()
        worker = JobWorker(process, _Jobs(job), retry_delay_seconds=60, stale_job_timeout_seconds=300)  # type: ignore[arg-type]

        self.assertTrue(worker.run_once())
        self.assertEqual(process.jobs, [job])

    def test_requeues_failed_job(self) -> None:
        job = ClaimedEmailJob("job-1", "account", "uid-1", "record-1")
        jobs = _Jobs(job)
        worker = JobWorker(
            _Process(RuntimeError("unavailable")),
            jobs,
            retry_delay_seconds=60,
            stale_job_timeout_seconds=300,
        )  # type: ignore[arg-type]

        self.assertTrue(worker.run_once())
        self.assertEqual(jobs.retries, [("job-1", "unavailable", 60)])
