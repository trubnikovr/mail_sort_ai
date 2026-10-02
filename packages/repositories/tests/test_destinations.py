import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mail_sort_database.models import Destination
from mail_sort_repositories import DestinationRepository


class DestinationRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        self.addCleanup(self.engine.dispose)
        Destination.__table__.create(self.engine)
        self.sessions = sessionmaker(self.engine)
        with self.sessions.begin() as session:
            session.add_all([
                Destination(id='ndr', account_id='a', name='NDR', description='Failures', mailbox='Inbox/NDR', is_active=True),
                Destination(id='off', account_id='a', name='Off', mailbox='Off', is_active=False),
                Destination(id='other', account_id='b', name='Other', mailbox='Other', is_active=True),
            ])
        self.repo = DestinationRepository(self.sessions)

    def test_only_active_destinations_for_account(self):
        records = self.repo.active_for_account('a')
        self.assertIsInstance(records, tuple)
        self.assertEqual([item.id for item in records], ['ndr'])
        self.assertEqual(records[0].description, 'Failures')
        self.assertEqual(self.repo.active_for_account('missing'), ())

    def test_lookup_rejects_other_account_disabled_and_missing(self):
        self.assertEqual(self.repo.get_active('a', 'ndr').mailbox, 'Inbox/NDR')
        for destination in ('other', 'off', 'missing'):
            with self.subTest(destination=destination), self.assertRaises(LookupError):
                self.repo.get_active('a', destination)
