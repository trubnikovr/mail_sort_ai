import unittest
from unittest.mock import Mock

from mail_decision.processing.context import ClaimedEmailJob, EmailContent, ProcessingContext
from mail_decision.processing.email_classification_process import EmailClassificationProcess
from mail_decision.processing.steps.rules.detect_ndr import DetectNdr
from mail_decision.processing.steps.email.get_email import GetEmail
from mail_decision.processing.steps.email.prepare_data import PrepareData
from mail_decision.processing.steps.limits.validate_ai_request import ValidateAiRequest
from mail_decision.processing.steps.limits.acquire_ai_request_permit import AcquireAiRequestPermit
from mail_decision.processing.steps.ai_rules.classify_by_body import ClassifyByBody


class DetectNdrTest(unittest.TestCase):
    def context(self, headers):
        return ProcessingContext(
            job=ClaimedEmailJob("job", "account", "message", "record"),
            email=EmailContent("sender", "Undeliverable", "Delivery failed", headers),
        )

    def test_provider_failure_signals(self):
        destinations = Mock()
        destinations.active_for_account.return_value = {"ndr": "NDR"}
        for headers in ({"delivery_status_actions": "failed"},
                        {"delivery_status_actions": "delivered,failed"},
                        {"item_class": "REPORT.IPM.Note.NDR"}):
            with self.subTest(headers=headers):
                context = self.context(headers)
                DetectNdr(destinations).execute(context)
                self.assertEqual(context.outcome.destination_id, "ndr")
                self.assertEqual(context.outcome.source, "ndr_rule")

    def test_keywords_success_delay_and_read_receipts_do_not_match(self):
        for headers in ({}, {"delivery_status_actions": "delayed"},
                        {"delivery_status_actions": "delivered"},
                        {"item_class": "REPORT.IPM.Note.IPNRN"}):
            context = self.context(headers)
            DetectNdr(Mock()).execute(context)
            self.assertIsNone(context.outcome)

    def test_missing_destination_fails_without_fallback(self):
        destinations = Mock()
        destinations.active_for_account.return_value = {}
        with self.assertRaisesRegex(ValueError, "ndr"):
            DetectNdr(destinations).execute(self.context({"delivery_status_actions": "failed"}))

    def test_ndr_finalizes_without_ai_or_quota(self):
        context = self.context({"delivery_status_actions": "failed"})
        reader, destinations, quota, classifier, results = (Mock() for _ in range(5))
        reader.read.return_value = context.email
        destinations.active_for_account.return_value = {"ndr": "NDR"}
        validate = ValidateAiRequest(destinations)
        process = EmailClassificationProcess([
            GetEmail(reader), DetectNdr(destinations), PrepareData(100), validate,
            AcquireAiRequestPermit(quota, "openai"),
            ClassifyByBody(classifier, .95),
        ], results=results)
        outcome = process.execute(context.job)
        quota.acquire.assert_not_called()
        classifier.classify_subject.assert_not_called()
        classifier.classify_body.assert_not_called()
        results.finalize.assert_called_once_with(context.job, outcome)
