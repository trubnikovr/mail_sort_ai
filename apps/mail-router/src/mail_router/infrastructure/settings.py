from dataclasses import dataclass
from os import environ, getenv
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    poll_interval_seconds: int
    retry_delay_seconds: int
    stale_job_timeout_seconds: int
    worker_id: str

    @classmethod
    def from_environment(cls) -> "Settings":
        cls._load_local_env()
        settings = cls(
            database_url=cls._required("DATABASE_URL"),
            poll_interval_seconds=cls._positive_int("ROUTER_POLL_INTERVAL_SECONDS", 10),
            retry_delay_seconds=cls._positive_int("RETRY_DELAY_SECONDS", 60),
            stale_job_timeout_seconds=cls._positive_int("STALE_JOB_TIMEOUT_SECONDS", 300),
            worker_id=getenv("ROUTER_WORKER_ID", "mail-router-1").strip(),
        )
        if not settings.worker_id:
            raise ValueError("ROUTER_WORKER_ID must not be empty")
        return settings

    @staticmethod
    def _required(name: str) -> str:
        value = getenv(name, "").strip()
        if not value:
            raise ValueError(f"{name} is required")
        return value

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
