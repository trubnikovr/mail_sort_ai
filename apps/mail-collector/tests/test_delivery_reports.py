import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from mail_collector.mailboxes.imap import ImapMailboxSource
from mail_collector.mailboxes.ews import EwsMailboxSource


def report(action):
    return (
        'From: mailer-daemon@example.com\r\n'
        'Subject: Delivery Status Notification\r\n'
        'Content-Type: multipart/report; report-type=delivery-status; boundary=x\r\n\r\n'
        '--x\r\nContent-Type: text/plain\r\n\r\nDelivery notification\r\n'
        '--x\r\nContent-Type: message/delivery-status\r\n\r\n'
        'Reporting-MTA: dns; example.com\r\n\r\n'
        f'Final-Recipient: rfc822; user@example.com\r\nAction: {action}\r\n'
        'Status: 5.1.1\r\n\r\n--x--\r\n'
    ).encode()


class DeliveryReportTest(unittest.TestCase):
    def read(self, raw):
        session = Mock()
        session.uid.return_value = ('OK', [(b'1', raw)])
        return ImapMailboxSource._read_message(session, 1)

    def test_preserves_delivery_actions(self):
        for action in ('failed', 'delayed', 'delivered'):
            self.assertEqual(self.read(report(action)).headers['delivery_status_actions'], action)

    def test_forwarded_report_is_not_top_level_ndr(self):
        raw = (b'Content-Type: multipart/mixed; boundary=outer\r\n\r\n'
               b'--outer\r\nContent-Type: text/plain\r\n\r\nPlease investigate\r\n'
               b'--outer\r\nContent-Type: message/rfc822\r\n\r\n' + report('failed') +
               b'\r\n--outer--\r\n')
        self.assertNotIn('delivery_status_actions', self.read(raw).headers)

    def test_ews_preserves_provider_item_class(self):
        item = SimpleNamespace(id='id', item_class='REPORT.IPM.Note.NDR')
        self.assertEqual(EwsMailboxSource._message(item).headers['item_class'], item.item_class)
