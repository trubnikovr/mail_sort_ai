import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from mail_decision.infrastructure.persistence import JobStore
from mail_decision.processing.context import ClaimedEmailJob, DailyRequestLimitReached
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
    def test_quota_pauses_claiming_and_resumes_after_deadline(self) -> None:
        job = ClaimedEmailJob("job-1", "account", "uid-1", "record-1")
        jobs = Mock()
        jobs.recover_stale.return_value = 0
        jobs.claim_next.return_value = job
        process = _Process(DailyRequestLimitReached("quota"))
        worker = JobWorker(process, jobs, 60, 300)
        with patch("mail_decision.processing.worker.monotonic", return_value=100) as clock, patch.object(
            DailyRequestLimitReached, "retry_delay_seconds", return_value=3600
        ):
            self.assertTrue(worker.run_once())
            jobs.defer.assert_called_once_with(job.id, process.error, 3600)
            jobs.retry.assert_not_called()
            clock.return_value = 3699
            self.assertFalse(worker.run_once())
            self.assertEqual(jobs.claim_next.call_count, 1)
            self.assertEqual(jobs.recover_stale.call_count, 1)
            clock.return_value = 3700
            process.error = None
            self.assertTrue(worker.run_once())
            self.assertEqual(jobs.claim_next.call_count, 2)

    def test_forever_sleeps_during_quota_pause(self) -> None:
        jobs = Mock()
        jobs.recover_stale.return_value = 0
        jobs.claim_next.return_value = ClaimedEmailJob("job-1", "account", "uid-1", "record-1")
        worker = JobWorker(_Process(DailyRequestLimitReached("quota")), jobs, 60, 300)
        with patch("mail_decision.processing.worker.monotonic", return_value=100), patch.object(
            DailyRequestLimitReached, "retry_delay_seconds", return_value=3600
        ), patch("mail_decision.processing.worker.sleep", side_effect=KeyboardInterrupt) as sleep:
            with self.assertRaises(KeyboardInterrupt):
                worker.run_forever(5)
            sleep.assert_called_once_with(3600)
            jobs.claim_next.assert_called_once()

    def test_defer_restores_last_attempt_and_releases_job(self) -> None:
        job = Mock(status="processing", locked_by="worker", attempts=5, max_attempts=5)
        sessions = Mock()
        with patch("mail_decision.infrastructure.persistence.session_scope") as scope:
            scope.return_value.__enter__.return_value.get.return_value = job
            JobStore(sessions, "worker").defer(str(uuid4()), DailyRequestLimitReached("quota"), 3600)
        self.assertEqual(job.status, "pending")
        self.assertEqual(job.attempts, 4)
        self.assertEqual(job.last_error, "quota")
        self.assertIsNone(job.locked_at)
        self.assertIsNone(job.locked_by)

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
