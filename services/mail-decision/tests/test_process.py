import unittest

from mail_sort_contracts import ClassificationDecision

from mail_decision.classification.service import ClassificationResponse
from mail_decision.processing.context import ClaimedEmailJob, EmailContent
from mail_decision.processing.email_classification_process import EmailClassificationProcess
from mail_decision.processing.steps.ai_rules.classify_by_body import ClassifyByBody
from mail_decision.processing.steps.disabled.classify_by_subject import ClassifyBySubject
from mail_decision.processing.steps.email.get_email import GetEmail
from mail_decision.processing.steps.email.prepare_data import PrepareData
from mail_decision.processing.steps.limits.validate_ai_request import ValidateAiRequest
from mail_decision.processing.steps.limits.acquire_ai_request_permit import AcquireAiRequestPermit


class _Reader:
    def read(self, _: ClaimedEmailJob) -> EmailContent:
        return EmailContent(subject=" Invoice ", sender=" billing@example.com ", body="abcdef")


class _Destinations:
    def active_for_account(self, _: str) -> dict[str, str]:
        return {"finance": "Finance", "work": "Work", "needs-review": "Needs review"}


class _Classifier:
    def __init__(self, subject_decision: ClassificationDecision | None, body_decision: ClassificationDecision):
        self.subject_decision = subject_decision
        self.body_decision = body_decision
        self.subject_calls = 0
        self.body_calls = 0

    def classify_subject(
        self,
        sender: str,
        subject: str,
        destinations: dict[str, str],
    ) -> ClassificationResponse:
        self.subject_calls += 1
        self.subject_email = (sender, subject, destinations)
        if self.subject_decision is None:
            return ClassificationResponse(action="need_body", reason="Not enough information")
        return self._as_response(self.subject_decision)

    def classify_body(
        self,
        sender: str,
        subject: str,
        body: str,
        destinations: dict[str, str],
    ) -> ClassificationResponse:
        self.body_calls += 1
        self.email = EmailContent(sender=sender, subject=subject, body=body)
        return self._as_response(self.body_decision)

    @staticmethod
    def _as_response(decision: ClassificationDecision) -> ClassificationResponse:
        return ClassificationResponse(
            action="classified",
            category=decision.category,
            destination_id=decision.destination_id,
            confidence=decision.confidence,
            reason=decision.reason,
        )


class _Quota:
    def acquire(self, _: str) -> bool:
        return True


class _Results:
    def __init__(self) -> None:
        self.finalized = []

    def finalize(self, job: ClaimedEmailJob, outcome: object) -> None:
        self.finalized.append((job.id, outcome))


class ProcessTest(unittest.TestCase):
    def _process(self, subject_decision: ClassificationDecision | None, body_decision: ClassificationDecision):
        classifier, results = _Classifier(subject_decision, body_decision), _Results()
        return (
            EmailClassificationProcess(
                steps=[
                    GetEmail(_Reader()),
                    PrepareData(3),
                    ValidateAiRequest(_Destinations()),
                    AcquireAiRequestPermit(_Quota(), "gemini"),
                    ClassifyBySubject(classifier, 0.95),
                    ValidateAiRequest(_Destinations()),
                    AcquireAiRequestPermit(_Quota(), "gemini"),
                    ClassifyByBody(classifier, 0.9),
                ],
                results=results,
            ), classifier, results,
        )

    def test_confident_subject_skips_body_and_applies_label(self) -> None:
        process, classifier, results = self._process(
            ClassificationDecision("Work", "work", 0.99, "Subject match"),
            ClassificationDecision("Work", "work", 1.0, "unused"),
        )
        outcome = process.execute(ClaimedEmailJob("job-1", "account", "uid-1", "record-1"))
        self.assertEqual(outcome.source, "ai_subject")
        self.assertEqual((classifier.subject_calls, classifier.body_calls), (1, 0))
        self.assertEqual(results.finalized, [("job-1", outcome)])

    def test_subject_need_body_falls_back_to_prepared_body(self) -> None:
        process, classifier, results = self._process(
            None,
            ClassificationDecision("Finance", "finance", 0.4, "ambiguous"),
        )
        outcome = process.execute(ClaimedEmailJob("job-1", "account", "uid-1", "record-1"))
        self.assertEqual((outcome.source, outcome.status), ("ai_body", "review"))
        self.assertEqual(outcome.destination_id, "needs-review")
        self.assertEqual(classifier.email.body, "abc")
        self.assertEqual(results.finalized, [("job-1", outcome)])


class ProcessControlTest(unittest.TestCase):
    def test_stops_after_outcome_and_finalizes_once(self):
        from unittest.mock import Mock
        from mail_decision.processing.context import ProcessingOutcome

        outcome = ProcessingOutcome("completed", "ndr", "ndr_rule", None, "NDR")
        first, later, results = Mock(), Mock(), Mock()
        first.execute.side_effect = lambda context: setattr(context, "outcome", outcome)
        job = ClaimedEmailJob("job", "account", "message", "record")
        process = EmailClassificationProcess([first, later], results)
        self.assertEqual(process.execute(job), outcome)
        later.execute.assert_not_called()
        results.finalize.assert_called_once_with(job, outcome)

    def test_step_errors_propagate_without_finalization(self):
        from unittest.mock import Mock
        from mail_decision.processing.context import DailyRequestLimitReached

        for error in (DailyRequestLimitReached("quota"), ValueError("invalid")):
            with self.subTest(error=type(error).__name__):
                step, later, results = Mock(), Mock(), Mock()
                step.execute.side_effect = error
                process = EmailClassificationProcess([step, later], results)
                with self.assertRaises(type(error)) as raised:
                    process.execute(ClaimedEmailJob("job", "account", "message", "record"))
                self.assertIs(raised.exception, error)
                later.execute.assert_not_called()
                results.finalize.assert_not_called()

    def test_missing_outcome_does_not_finalize(self):
        from unittest.mock import Mock

        results = Mock()
        with self.assertRaisesRegex(RuntimeError, "without an outcome"):
            EmailClassificationProcess([], results).execute(
                ClaimedEmailJob("job", "account", "message", "record")
            )
        results.finalize.assert_not_called()

    def test_finalization_error_propagates(self):
        from unittest.mock import Mock
        from mail_decision.processing.context import ProcessingOutcome

        step, results = Mock(), Mock()
        step.execute.side_effect = lambda context: setattr(
            context, "outcome", ProcessingOutcome("completed", "ndr", "ndr_rule", None, "NDR")
        )
        results.finalize.side_effect = RuntimeError("database unavailable")
        with self.assertRaisesRegex(RuntimeError, "database unavailable"):
            EmailClassificationProcess([step], results).execute(
                ClaimedEmailJob("job", "account", "message", "record")
            )
        results.finalize.assert_called_once()
