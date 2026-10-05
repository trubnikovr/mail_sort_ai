from dataclasses import dataclass
from os import environ, getenv
from pathlib import Path

from mail_sort_contracts import MailProvider


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    mailbox_provider: MailProvider
    mailbox_account_id: str
    mailbox_source: str
    poll_interval_seconds: int
    imap_host: str | None = None
    imap_port: int = 993
    imap_username: str | None = None
    imap_app_password: str | None = None
    ews_endpoint: str | None = None
    ews_username: str | None = None
    ews_password: str | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        cls._load_local_env()
        provider = getenv("MAILBOX_PROVIDER", "imap").strip().lower()
        if provider not in {"imap", "ews"}:
            raise ValueError("MAILBOX_PROVIDER must be either 'imap' or 'ews'")
        settings = cls(
            database_url=cls._required("DATABASE_URL"),
            mailbox_provider=provider,  # type: ignore[arg-type]
            mailbox_account_id=cls._required("MAILBOX_ACCOUNT_ID"),
            mailbox_source=getenv("MAILBOX_SOURCE", "INBOX").strip(),
            imap_port=cls._positive_int("IMAP_PORT", default=993),
            imap_host=cls._optional("IMAP_HOST"),
            imap_username=cls._optional("IMAP_USERNAME"),
            imap_app_password=cls._optional("IMAP_APP_PASSWORD"),
            ews_endpoint=cls._optional("EWS_ENDPOINT"),
            ews_username=cls._optional("EWS_USERNAME"),
            ews_password=cls._optional("EWS_PASSWORD"),
            poll_interval_seconds=cls._positive_int(
                "COLLECTOR_POLL_INTERVAL_SECONDS",
                default=cls._positive_int("POLL_INTERVAL_SECONDS", default=60),
            ),
        )
        if not settings.mailbox_source:
            raise ValueError("MAILBOX_SOURCE must not be empty")
        if settings.mailbox_provider == "imap":
            settings._require_provider_values("IMAP", settings.imap_host, settings.imap_username, settings.imap_app_password)
        else:
            settings._require_provider_values("EWS", settings.ews_endpoint, settings.ews_username, settings.ews_password)
        return settings

    @staticmethod
    def _required(name: str) -> str:
        value = getenv(name, "").strip()
        if not value:
            raise ValueError(f"{name} is required")
        return value

    @staticmethod
    def _optional(name: str) -> str | None:
        return getenv(name, "").strip() or None

    @staticmethod
    def _require_provider_values(provider: str, *values: str | None) -> None:
        names = ("HOST", "USERNAME", "PASSWORD") if provider == "IMAP" else ("ENDPOINT", "USERNAME", "PASSWORD")
        missing = [f"{provider}_{name}" for name, value in zip(names, values) if not value]
        if missing:
            raise ValueError(f"{', '.join(missing)} required for MAILBOX_PROVIDER={provider.lower()}")

    @staticmethod
    def _load_local_env() -> None:
        """Load this service's local .env without overriding real environment values."""
        env_file = Path(__file__).resolve().parents[5] / ".env"
        if not env_file.exists():
            return
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or not key:
                continue
            environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

    @staticmethod
    def _positive_int(name: str, default: int) -> int:
        raw = getenv(name, str(default)).strip()
        try:
            value = int(raw)
        except ValueError as error:
            raise ValueError(f"{name} must be an integer") from error
        if value <= 0:
            raise ValueError(f"{name} must be positive")
        return value
