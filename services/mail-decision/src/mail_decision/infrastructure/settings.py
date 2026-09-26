from dataclasses import dataclass, field
from os import environ, getenv
from pathlib import Path


SUPPORTED_AI_PROVIDERS = frozenset({"gemini"})


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    mailbox_account_id: str
    ai_provider: str
    ai_model: str
    ai_api_key: str = field(repr=False)
    ai_confidence_threshold: float
    subject_confidence_threshold: float
    ai_max_requests_per_day: int
    ai_max_body_characters: int
    poll_interval_seconds: int
    retry_delay_seconds: int
    stale_job_timeout_seconds: int
    worker_id: str

    def __post_init__(self) -> None:
        if self.ai_provider not in SUPPORTED_AI_PROVIDERS:
            supported = ", ".join(sorted(SUPPORTED_AI_PROVIDERS))
            raise ValueError(
                f"AI_PROVIDER must be one of: {supported}; got {self.ai_provider!r}"
            )
        if not self.ai_model.strip():
            raise ValueError("AI_MODEL must not be empty")

    @classmethod
    def from_environment(cls) -> "Settings":
        cls._load_local_env()
        provider = getenv("AI_PROVIDER", "gemini").strip().lower()
        model = getenv("AI_MODEL", "gemini-3.5-flash-lite").strip()
        settings = cls(
            database_url=cls._required("DATABASE_URL"),
            mailbox_account_id=cls._required("MAILBOX_ACCOUNT_ID"),
            ai_provider=provider,
            ai_model=model,
            ai_api_key=cls._provider_api_key(provider),
            ai_confidence_threshold=cls._confidence_threshold(),
            subject_confidence_threshold=cls._probability("SUBJECT_CONFIDENCE_THRESHOLD", 0.95),
            ai_max_requests_per_day=cls._positive_int("AI_MAX_REQUESTS_PER_DAY", 200),
            ai_max_body_characters=cls._positive_int("AI_MAX_BODY_CHARS", 1000),
            poll_interval_seconds=cls._positive_int(
                "DECISION_POLL_INTERVAL_SECONDS",
                cls._positive_int("POLL_INTERVAL_SECONDS", 10),
            ),
            retry_delay_seconds=cls._positive_int("RETRY_DELAY_SECONDS", 60),
            stale_job_timeout_seconds=cls._positive_int("STALE_JOB_TIMEOUT_SECONDS", 300),
            worker_id=getenv("DECISION_WORKER_ID", "mail-decision-1").strip(),
        )
        if not settings.worker_id:
            raise ValueError("WORKER_ID must not be empty")
        return settings

    @staticmethod
    def _provider_api_key(provider: str) -> str:
        if provider == "gemini":
            value = (getenv("GOOGLE_API_KEY") or getenv("GEMINI_API_KEY") or "").strip()
            if value:
                return value
            raise ValueError("GOOGLE_API_KEY (or GEMINI_API_KEY) is required for AI_PROVIDER=gemini")
        return ""

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
    def _confidence_threshold() -> float:
        return Settings._probability("AI_CONFIDENCE_THRESHOLD", 0.9)

    @staticmethod
    def _probability(name: str, default: float) -> float:
        try:
            value = float(getenv(name, str(default)).strip())
        except ValueError as error:
            raise ValueError(f"{name} must be a number") from error
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be between 0 and 1")
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
