import unittest

from mail_sort_contracts import ClassificationDecision

from mail_decision.classification.service import ClassificationResponse
from mail_decision.processing.context import ClaimedEmailJob, EmailContent
from mail_decision.processing.email_classification_process import EmailClassificationProcess
from mail_decision.processing.steps.classify_by_body import ClassifyByBody
from mail_decision.processing.steps.classify_by_subject import ClassifyBySubject
from mail_decision.processing.steps.get_email import GetEmail
from mail_decision.processing.steps.mark_as_done import MarkAsDone
from mail_decision.processing.steps.prepare_data import PrepareData
from mail_decision.processing.steps.validate_ai_request import ValidateAiRequest


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
    def reserve(self, _: str) -> bool:
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
                    ValidateAiRequest(_Destinations(), _Quota(), "gemini"),
                    ClassifyBySubject(classifier, 0.95),
                    ValidateAiRequest(_Destinations(), _Quota(), "gemini"),
                    ClassifyByBody(classifier, 0.9),
                    MarkAsDone(results),
                ]
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
