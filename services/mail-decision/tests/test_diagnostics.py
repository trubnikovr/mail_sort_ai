import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from mail_decision.processing.context import ClaimedEmailJob, ProcessingOutcome, DailyRequestLimitReached
from mail_decision.processing.statistics.diagnostics import DiagnosticScope, current_diagnostics
from mail_decision.processing.email_classification_process import EmailClassificationProcess
from mail_decision.infrastructure.ai_agent import AiAgent
from mail_decision.classification.service import ClassificationResponse
from mail_decision.infrastructure.diagnostics import DatabaseDiagnosticStore


class DiagnosticsTest(unittest.TestCase):
    def test_decision_and_finalization_share_attempt(self):
        store, step, later, results = Mock(), Mock(), Mock(), Mock()
        step.execute.side_effect = lambda ctx: setattr(ctx, "outcome", ProcessingOutcome(
            "completed", "ndr", "ndr_rule", None, "NDR"))
        job = ClaimedEmailJob(str(uuid4()), "account", "message", "record", attempt=3)
        EmailClassificationProcess([step, later], results, store).execute(job)
        rows = [call.args[1] for call in store.record.call_args_list]
        self.assertEqual([r['status'] for r in rows], ['started', 'decision_made', 'started', 'completed'])
        self.assertEqual(len({r['run_id'] for r in rows}), 1)
        self.assertTrue(all(r['attempt'] == 3 for r in rows))
        self.assertEqual(rows[-1]['step'], 'finalize')
        self.assertEqual(rows[-1]['details']['decision_step'], 'Mock')
        later.execute.assert_not_called()
        self.assertIsNone(current_diagnostics.get())

    def test_quota_and_finalization_failure_are_distinguished(self):
        for phase in ('step', 'finalize'):
            store, step, results = Mock(), Mock(), Mock()
            if phase == 'step':
                step.execute.side_effect = DailyRequestLimitReached('private data')
            else:
                step.execute.side_effect = lambda ctx: setattr(ctx, 'outcome', ProcessingOutcome(
                    'completed', 'ndr', 'ndr_rule', None, 'NDR'))
                results.finalize.side_effect = RuntimeError('private data')
            with self.assertRaises(Exception):
                EmailClassificationProcess([step], results, store).execute(
                    ClaimedEmailJob(str(uuid4()), 'a', 'm', 'r'))
            row = store.record.call_args.args[1]
            self.assertEqual(row['status'], 'deferred' if phase == 'step' else 'failed')
            self.assertEqual(row['details']['finalization'], 'not_started' if phase == 'step' else 'failed')
            self.assertNotIn('private data', str(store.record.call_args_list))
            self.assertIsNone(current_diagnostics.get())

    def test_diagnostic_failure_does_not_repeat_committed_finalization(self):
        store, step, results = Mock(), Mock(), Mock()
        store.record.side_effect = RuntimeError('secret')
        step.execute.side_effect = lambda ctx: setattr(ctx, 'outcome', ProcessingOutcome(
            'completed', 'ndr', 'ndr_rule', None, 'NDR'))
        with self.assertLogs('mail_decision.processing.statistics.diagnostics', level='ERROR') as logs:
            EmailClassificationProcess([step], results, store).execute(
                ClaimedEmailJob(str(uuid4()), 'a', 'm', 'r'))
        results.finalize.assert_called_once()
        self.assertNotIn('secret', str(logs.output))

    def test_invalid_model_response_is_recorded_without_private_text(self):
        store = Mock()
        scope = DiagnosticScope(store, str(uuid4()), str(uuid4()), 1, 'ClassifyByBody', 7, {'ndr'})
        token = current_diagnostics.set(scope)
        try:
            with patch('mail_decision.infrastructure.ai_agent.init_chat_model') as factory:
                raw = Mock(content='{"action":"classified","destination_id":"ndr","confidence":0.8,"reason":"private body"}',
                           tool_calls=[], usage_metadata={'input_tokens': 12, 'output_tokens': 8, 'total_tokens': 20})
                factory.return_value.with_structured_output.return_value.invoke.return_value = {
                    'raw': raw, 'parsed': None, 'parsing_error': ValueError('private body')}
                with self.assertRaises(ValueError):
                    AiAgent('openai', 'test-model', 'secret').ask([('human', 'private body')], ClassificationResponse)
            rows = [call.args[1] for call in store.record.call_args_list]
            self.assertEqual([r['status'] for r in rows], ['started', 'response_received', 'failed'])
            self.assertEqual(rows[1]['details']['response']['destination_id'], 'ndr')
            self.assertEqual(rows[1]['details']['validation'], 'invalid')
            self.assertEqual(rows[1]['details']['tokens']['total_tokens'], 20)
            self.assertNotIn('private body', str(rows))
            self.assertNotIn('secret', str(rows))
        finally:
            current_diagnostics.reset(token)

    def test_store_opens_independent_transaction_per_event(self):
        with patch('mail_decision.infrastructure.diagnostics.session_scope') as transaction:
            store = DatabaseDiagnosticStore(Mock())
            values = dict(job_id=str(uuid4()), run_id=str(uuid4()), attempt=1,
                          step='GetEmail', step_number=1, status='started', details={})
            store.record('step', values)
            store.record('ai', values)
            self.assertEqual(transaction.call_count, 2)
            self.assertEqual(transaction.return_value.__exit__.call_count, 2)
