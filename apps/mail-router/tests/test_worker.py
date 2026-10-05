import unittest
from types import SimpleNamespace
from unittest.mock import patch

from mail_router.bootstrap import build_worker

from mail_router.routing.registry import MailboxActionRegistry
from mail_router.routing.tasks import ClaimedRouteJob
from mail_router.routing.worker import MailboxActionWorker


class _Jobs:
    def __init__(self, job: ClaimedRouteJob | None) -> None:
        self.job = job
        self.completed = []
        self.retries = []

    def claim_next(self) -> ClaimedRouteJob | None:
        job, self.job = self.job, None
        return job

    def recover_stale(self, _: int) -> int:
        return 0

    def complete(self, job_id: str) -> None:
        self.completed.append(job_id)

    def retry(self, job_id: str, error: Exception, retry_delay_seconds: int) -> None:
        self.retries.append((job_id, str(error), retry_delay_seconds))


class _ImapAction:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.jobs = []

    def move_to_folder(self, job: ClaimedRouteJob) -> None:
        self.jobs.append(job)
        if self.error:
            raise self.error


class MailboxActionWorkerTest(unittest.TestCase):
    def test_continuous_mode_drains_queue_then_waits_and_polls_again(self) -> None:
        worker = MailboxActionWorker(
            MailboxActionRegistry([]), _Jobs(None),
            retry_delay_seconds=60, stale_job_timeout_seconds=300,
        )  # type: ignore[arg-type]
        events = []
        results = iter([True, True, False, True])

        def run_once():
            events.append("poll")
            try:
                return next(results)
            except StopIteration:
                raise KeyboardInterrupt

        with (
            patch.object(worker, "run_once", side_effect=run_once),
            patch("mail_router.routing.worker.sleep", side_effect=lambda delay: events.append(("sleep", delay))),
        ):
            with self.assertRaises(KeyboardInterrupt):
                worker.run_forever(10)

        self.assertEqual(events, ["poll", "poll", "poll", ("sleep", 10), "poll", "poll"])

    def test_bootstrap_dispatches_route_to_configured_provider(self) -> None:
        job = ClaimedRouteJob("route-1", "account", "ews", "uid-1", "move", "work")
        jobs = _Jobs(job)
        action = _ImapAction()
        settings = SimpleNamespace(
            database_url="unused", mailbox_provider="ews", worker_id="test-worker",
            retry_delay_seconds=60, stale_job_timeout_seconds=300,
        )
        with (
            patch("mail_router.bootstrap.create_session_factory"),
            patch("mail_router.bootstrap.DestinationRepository"),
            patch("mail_router.bootstrap.RouteJobStore", return_value=jobs),
            patch("mail_router.bootstrap.MailboxActionFactory") as factory,
        ):
            factory.return_value.resolve.return_value = action
            worker = build_worker(settings)  # type: ignore[arg-type]

        self.assertTrue(worker.run_once())
        self.assertEqual(action.jobs, [job])
        self.assertEqual(jobs.completed, ["route-1"])
        self.assertEqual(jobs.retries, [])

    def test_completes_a_route(self) -> None:
        job = ClaimedRouteJob("route-1", "account", "imap", "uid-1", "move", "work")
        jobs = _Jobs(job)
        action = _ImapAction()
        worker = MailboxActionWorker(
            MailboxActionRegistry([("imap", action)]),
            jobs,
            retry_delay_seconds=60,
            stale_job_timeout_seconds=300,
        )  # type: ignore[arg-type]

        self.assertTrue(worker.run_once())
        self.assertEqual(action.jobs, [job])
        self.assertEqual(jobs.completed, ["route-1"])

    def test_retries_a_failed_route(self) -> None:
        job = ClaimedRouteJob("route-1", "account", "imap", "uid-1", "move", "work")
        jobs = _Jobs(job)
        worker = MailboxActionWorker(
            MailboxActionRegistry([("imap", _ImapAction(RuntimeError("unavailable")))]),
            jobs,
            retry_delay_seconds=60,
            stale_job_timeout_seconds=300,
        )  # type: ignore[arg-type]

        self.assertTrue(worker.run_once())
        self.assertEqual(jobs.retries, [("route-1", "unavailable", 60)])
