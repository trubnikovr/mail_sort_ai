import unittest
from email import policy
from email.parser import BytesParser

from mail_collector.mailboxes.email_body import extract_body


def _message(source: bytes):
    return BytesParser(policy=policy.default).parsebytes(source)


class EmailBodyTest(unittest.TestCase):
    def test_prefers_plain_text_over_html_alternative(self) -> None:
        message = _message(
            b"Content-Type: multipart/alternative; boundary=part\r\n\r\n"
            b"--part\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nPlain message\r\n"
            b"--part\r\nContent-Type: text/html; charset=utf-8\r\n\r\n<p>HTML message</p>\r\n"
            b"--part--\r\n"
        )

        self.assertEqual(extract_body(message), "Plain message")

    def test_ignores_html_when_plain_text_is_missing(self) -> None:
        message = _message(
            b"Content-Type: text/html; charset=utf-8\r\n\r\n"
            b"<style>.hidden { display: none }</style><p>Hello&nbsp;<b>world</b></p>"
            b"<script>alert('ignore')</script><div>Invoice &amp; receipt</div>"
        )

        self.assertEqual(extract_body(message), "")

    def test_ignores_text_attachments(self) -> None:
        message = _message(
            b"Content-Type: multipart/mixed; boundary=part\r\n\r\n"
            b"--part\r\nContent-Type: text/plain; charset=utf-8\r\n\r\nVisible text\r\n"
            b"--part\r\nContent-Type: text/plain; charset=utf-8\r\n"
            b"Content-Disposition: attachment; filename=secret.txt\r\n\r\nDo not include\r\n"
            b"--part--\r\n"
        )

        self.assertEqual(extract_body(message), "Visible text")
