import os
import unittest
from unittest.mock import patch

from mail_decision.infrastructure.settings import Settings


class SettingsTest(unittest.TestCase):
    def _settings(self, **changes: object) -> Settings:
        values: dict[str, object] = {
            "database_url": "postgresql://postgres@localhost/mail_sort",
            "mailbox_account_id": "personal-gmail",
            "ai_provider": "gemini",
            "ai_model": "some-model",
            "ai_api_key": "test-key",
            "ai_confidence_threshold": 0.9,
            "subject_confidence_threshold": 0.95,
            "ai_max_requests_per_day": 200,
            "ai_max_body_characters": 1000,
            "poll_interval_seconds": 10,
            "retry_delay_seconds": 60,
            "stale_job_timeout_seconds": 300,
            "worker_id": "test-worker",
        }
        values.update(changes)
        return Settings(**values)  # type: ignore[arg-type]

    def test_rejects_unknown_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "AI_PROVIDER"):
            self._settings(ai_provider="unknown")

    def test_rejects_empty_model(self) -> None:
        with self.assertRaisesRegex(ValueError, "AI_MODEL"):
            self._settings(ai_model="  ")

    def test_requires_gemini_key_from_environment(self) -> None:
        environment = dict(os.environ)
        environment.pop("GOOGLE_API_KEY", None)
        environment.pop("GEMINI_API_KEY", None)
        environment.update(
            {
                "DATABASE_URL": "postgresql://postgres@localhost/mail_sort",
                "MAILBOX_ACCOUNT_ID": "personal-gmail",
                "IMAP_HOST": "imap.gmail.com",
                "IMAP_USERNAME": "mail@example.com",
                "IMAP_APP_PASSWORD": "test-password",
            }
        )
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(ValueError, "GOOGLE_API_KEY"):
                Settings.from_environment()

    def test_accepts_valid_gemini_configuration(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "GEMINI",
                "AI_MODEL": "gemini-3.5-flash-lite",
                "GOOGLE_API_KEY": "test-key",
                "DATABASE_URL": "postgresql://postgres@localhost/mail_sort",
                "MAILBOX_ACCOUNT_ID": "personal-gmail",
                "IMAP_HOST": "imap.gmail.com",
                "IMAP_USERNAME": "mail@example.com",
                "IMAP_APP_PASSWORD": "test-password",
            },
            clear=True,
        ):
            settings = Settings.from_environment()

        self.assertEqual(settings.ai_provider, "gemini")
        self.assertEqual(settings.ai_model, "gemini-3.5-flash-lite")
