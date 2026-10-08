from dataclasses import dataclass
from os import environ, getenv
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    poll_interval_seconds: int

    @classmethod
    def from_environment(cls) -> "Settings":
        cls._load_local_env()
        return cls(
            database_url=cls._required("DATABASE_URL"),
            poll_interval_seconds=cls._positive_int(
                "COLLECTOR_POLL_INTERVAL_SECONDS",
                cls._positive_int("POLL_INTERVAL_SECONDS", 60),
            ),
        )

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
