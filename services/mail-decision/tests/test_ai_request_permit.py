import unittest
from unittest.mock import Mock

from mail_decision.processing.context import ClaimedEmailJob, DailyRequestLimitReached, ProcessingContext
from mail_decision.processing.email_classification_process import EmailClassificationProcess
from mail_decision.processing.steps.limits.acquire_ai_request_permit import AcquireAiRequestPermit
from mail_decision.processing.steps.limits.validate_ai_request import ValidateAiRequest


class AiRequestPermitTest(unittest.TestCase):
    def test_invalid_configuration_does_not_consume_permit(self):
        destinations, quota, classifier, results = (Mock() for _ in range(4))
        destinations.active_for_account.return_value = {}
        process = EmailClassificationProcess([
            ValidateAiRequest(destinations), AcquireAiRequestPermit(quota, 'openai'), classifier,
        ], results)
        with self.assertRaises(ValueError):
            process.execute(ClaimedEmailJob('job', 'account', 'message', 'record'))
        quota.acquire.assert_not_called()
        classifier.execute.assert_not_called()
        results.finalize.assert_not_called()

    def test_exhausted_quota_stops_before_ai(self):
        quota, classifier, results = Mock(), Mock(), Mock()
        quota.acquire.return_value = False
        process = EmailClassificationProcess([
            AcquireAiRequestPermit(quota, 'openai'), classifier,
        ], results)
        with self.assertRaises(DailyRequestLimitReached):
            process.execute(ClaimedEmailJob('job', 'account', 'message', 'record'))
        quota.acquire.assert_called_once_with('openai')
        classifier.execute.assert_not_called()
        results.finalize.assert_not_called()

    def test_permit_consumed_once_without_creating_decision(self):
        quota = Mock()
        quota.acquire.return_value = True
        context = ProcessingContext(ClaimedEmailJob('job', 'account', 'message', 'record'))
        AcquireAiRequestPermit(quota, 'openai').execute(context)
        quota.acquire.assert_called_once_with('openai')
        self.assertIsNone(context.outcome)
