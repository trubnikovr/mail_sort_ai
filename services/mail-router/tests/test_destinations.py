import unittest
from unittest.mock import Mock, patch

from mail_sort_repositories import DestinationRecord
from mail_router.infrastructure.persistence import DestinationRepository


class DestinationsTest(unittest.TestCase):
    def test_resolves_mailbox_through_shared_repository(self):
        with patch('mail_router.infrastructure.persistence.SharedDestinationRepository') as shared:
            shared.return_value.get_active.return_value = DestinationRecord('ndr', 'NDR', '', 'Inbox/NDR')
            self.assertEqual(DestinationRepository(Mock()).mailbox_for('account', 'ndr'), 'Inbox/NDR')
            shared.return_value.get_active.assert_called_once_with('account', 'ndr')
