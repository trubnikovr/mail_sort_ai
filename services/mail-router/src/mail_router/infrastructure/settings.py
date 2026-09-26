from dataclasses import dataclass
from os import environ, getenv
from pathlib import Path

from mail_sort_contracts import MailProvider


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    poll_interval_seconds: int
    retry_delay_seconds: int
    stale_job_timeout_seconds: int
    worker_id: str
    mailbox_provider: MailProvider
    mailbox_source: str
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
            poll_interval_seconds=cls._positive_int("ROUTER_POLL_INTERVAL_SECONDS", 10),
            retry_delay_seconds=cls._positive_int("RETRY_DELAY_SECONDS", 60),
            stale_job_timeout_seconds=cls._positive_int("STALE_JOB_TIMEOUT_SECONDS", 300),
            worker_id=getenv("ROUTER_WORKER_ID", "mail-router-1").strip(),
            mailbox_provider=provider,  # type: ignore[arg-type]
            mailbox_source=getenv("MAILBOX_SOURCE", "INBOX").strip(),
            imap_port=cls._positive_int("IMAP_PORT", 993),
            imap_host=cls._optional("IMAP_HOST"),
            imap_username=cls._optional("IMAP_USERNAME"),
            imap_app_password=cls._optional("IMAP_APP_PASSWORD"),
            ews_endpoint=cls._optional("EWS_ENDPOINT"),
            ews_username=cls._optional("EWS_USERNAME"),
            ews_password=cls._optional("EWS_PASSWORD"),
        )
        if not settings.worker_id:
            raise ValueError("ROUTER_WORKER_ID must not be empty")
        if not settings.mailbox_source:
            raise ValueError("MAILBOX_SOURCE must not be empty")
        values = (
            (settings.imap_host, settings.imap_username, settings.imap_app_password)
            if provider == "imap"
            else (settings.ews_endpoint, settings.ews_username, settings.ews_password)
        )
        if any(not value for value in values):
            raise ValueError(f"{provider.upper()} connection settings are required")
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
    def _positive_int(name: str, default: int) -> int:
        try:
            value = int(getenv(name, str(default)).strip())
        except ValueError as error:
            raise ValueError(f"{name} must be an integer") from error
        if value <= 0:
            raise ValueError(f"{name} must be positive")
        return value

    @staticmethod
    def _load_local_env() -> None:
        env_file = Path(__file__).resolve().parents[5] / ".env"
        if not env_file.exists():
            return
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if separator and key:
                environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
