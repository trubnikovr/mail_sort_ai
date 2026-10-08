from dataclasses import dataclass
from os import environ, getenv
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    mailbox_account_id: str
    database_url: str
    ews_endpoint: str | None = None
    ews_username: str | None = None
    ews_password: str | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        cls._load_local_env()
        settings = cls(
            mailbox_account_id=cls._required("MAILBOX_ACCOUNT_ID"),
            database_url=cls._required("DATABASE_URL"),
            ews_endpoint=cls._optional("EWS_ENDPOINT"),
            ews_username=cls._optional("EWS_USERNAME"),
            ews_password=cls._optional("EWS_PASSWORD"),
        )
        credentials = (settings.ews_endpoint, settings.ews_username, settings.ews_password)
        if any(not value for value in credentials):
            raise ValueError("EWS connection settings are required")
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
    def _load_local_env() -> None:
        env_file = Path(__file__).resolve().parents[4] / ".env"
        if not env_file.exists():
            return
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if separator and key:
                environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
