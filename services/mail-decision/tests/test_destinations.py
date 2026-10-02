import unittest
from unittest.mock import Mock, patch

from mail_sort_repositories import DestinationRecord
from mail_decision.infrastructure.persistence import DestinationRepository


class DestinationsTest(unittest.TestCase):
    def test_formats_shared_records_for_ai(self):
        with patch('mail_decision.infrastructure.persistence.SharedDestinationRepository') as shared:
            shared.return_value.active_for_account.return_value = (
                DestinationRecord('ndr', 'NDR', 'Failures', 'Inbox/NDR'),
                DestinationRecord('review', 'Review', '', 'Review'),
            )
            self.assertEqual(DestinationRepository(Mock()).active_for_account('account'),
                             {'ndr': 'NDR — Failures', 'review': 'Review'})
            shared.return_value.active_for_account.assert_called_once_with('account')
