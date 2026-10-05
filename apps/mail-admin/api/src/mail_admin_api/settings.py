from dataclasses import dataclass
from os import environ, getenv
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    admin_username: str
    admin_password: str
    session_secret: str
    host: str = "127.0.0.1"
    port: int = 8082
    cookie_secure: bool = False
    session_max_age_seconds: int = 31_536_000

    @classmethod
    def from_environment(cls) -> "Settings":
        env_file = Path(__file__).resolve().parents[5] / ".env"
        if env_file.exists():
            for raw_line in env_file.read_text().splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                key, separator, value = line.partition("=")
                if separator:
                    environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        database_url = getenv("DATABASE_URL", "").strip()
        if not database_url:
            raise ValueError("DATABASE_URL is required")
        username = getenv("MAIL_ADMIN_USERNAME", "").strip()
        password = getenv("MAIL_ADMIN_PASSWORD", "")
        session_secret = getenv("MAIL_ADMIN_SESSION_SECRET", "")
        if not username:
            raise ValueError("MAIL_ADMIN_USERNAME is required")
        if not password or password.startswith("replace-"):
            raise ValueError("MAIL_ADMIN_PASSWORD must be configured")
        if len(session_secret) < 32 or session_secret.startswith("replace-"):
            raise ValueError("MAIL_ADMIN_SESSION_SECRET must be a random secret of at least 32 characters")
        try:
            port = int(getenv("ADMIN_PORT", "8082"))
        except ValueError as error:
            raise ValueError("ADMIN_PORT must be an integer") from error
        if not 1 <= port <= 65535:
            raise ValueError("ADMIN_PORT must be between 1 and 65535")
        try:
            session_max_age = int(getenv("MAIL_ADMIN_SESSION_MAX_AGE_SECONDS", "31536000"))
        except ValueError as error:
            raise ValueError("MAIL_ADMIN_SESSION_MAX_AGE_SECONDS must be an integer") from error
        if session_max_age < 300:
            raise ValueError("MAIL_ADMIN_SESSION_MAX_AGE_SECONDS must be at least 300")
        cookie_secure_value = getenv("MAIL_ADMIN_COOKIE_SECURE", "false").strip().lower()
        if cookie_secure_value not in {"true", "false", "1", "0", "yes", "no"}:
            raise ValueError("MAIL_ADMIN_COOKIE_SECURE must be true or false")
        return cls(
            database_url=database_url,
            admin_username=username,
            admin_password=password,
            session_secret=session_secret,
            host=getenv("ADMIN_HOST", "127.0.0.1").strip(),
            port=port,
            cookie_secure=cookie_secure_value in {"true", "1", "yes"},
            session_max_age_seconds=session_max_age,
        )
