from dataclasses import dataclass
from os import environ, getenv
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    mailbox_account_id: str
    ews_endpoint: str
    ews_username: str
    ews_password: str

    @classmethod
    def from_environment(cls) -> "Settings":
        cls._load_local_env()
        return cls(
            database_url=cls._required("DATABASE_URL"),
            mailbox_account_id=cls._required("MAILBOX_ACCOUNT_ID"),
            ews_endpoint=cls._required("EWS_ENDPOINT"),
            ews_username=cls._required("EWS_USERNAME"),
            ews_password=cls._required("EWS_PASSWORD"),
        )

    @staticmethod
    def _required(name: str) -> str:
        value = getenv(name, "").strip()
        if not value:
            raise ValueError(f"{name} is required")
        return value

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
