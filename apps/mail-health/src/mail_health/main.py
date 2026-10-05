import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from os import environ, getenv
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config
from mail_sort_database.session import create_engine_from_url
from sqlalchemy.engine import Engine
from mail_sort_logging import configure_logging
from sqlalchemy import text


logger = logging.getLogger(__name__)


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


def check_ai() -> tuple[bool, str]:
    provider = getenv("AI_PROVIDER", "openai").strip().lower()
    model = getenv("AI_MODEL", "").strip()
    api_key = getenv("AI_AGENT_API_KEY", "").strip()
    if not model or not api_key:
        return False, "configuration_missing"
    if provider == "openai":
        url = f"https://api.openai.com/v1/models/{quote(model, safe='')}"
        headers = {"Authorization": f"Bearer {api_key}"}
    elif provider == "gemini":
        model_name = model.removeprefix("models/")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model_name, safe='')}"
        headers = {"x-goog-api-key": api_key}
    else:
        return False, "unsupported_provider"
    try:
        with urlopen(Request(url, headers=headers), timeout=5) as response:
            if not 200 <= response.status < 300:
                return False, "http_error"
            return True, "available"
    except HTTPError as error:
        return False, f"http_{error.code}"
    except (URLError, TimeoutError, OSError):
        return False, "unreachable"


def check_aws() -> str:
    region = getenv("AWS_REGION", getenv("AWS_DEFAULT_REGION", "")).strip()
    if not region:
        return "not_configured"
    try:
        sts = boto3.Session(region_name=region).client(
            "sts",
            config=Config(connect_timeout=3, read_timeout=3, retries={"max_attempts": 0}),
        )
        sts.get_caller_identity()
        return "available"
    except Exception as error:
        logger.warning("health dependency failed: dependency=aws_sts error_type=%s", type(error).__name__)
        return "unavailable"


def check_mail_services() -> tuple[str, dict[str, object]]:
    url = getenv("MAIL_APP_HEALTH_URL", "").strip()
    if not url:
        return "not_configured", {}
    try:
        with urlopen(url, timeout=3) as response:
            payload = json.loads(response.read(64_000))
            services = payload.get("services", {})
            if response.status == 200 and payload.get("status") == "ready":
                return "available", services
            return "unavailable", services
    except HTTPError as error:
        try:
            payload = json.loads(error.read(64_000))
            return "unavailable", payload.get("services", {})
        except (ValueError, OSError):
            return "unavailable", {}
    except (URLError, TimeoutError, OSError, ValueError):
        return "unavailable", {}


def build_health(database_engine: Engine) -> dict[str, object]:
    checks: dict[str, str] = {}
    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["postgres"] = "available"
    except Exception as error:
        logger.warning("health dependency failed: dependency=postgres error_type=%s", type(error).__name__)
        checks["postgres"] = "unavailable"
    _, ai_status = check_ai()
    checks["ai_provider"] = ai_status
    checks["aws"] = check_aws()
    mail_services_status, mail_services = check_mail_services()
    checks["mail_services"] = mail_services_status
    required_checks = (checks["postgres"], checks["ai_provider"])
    required_checks_ok = all(value == "available" for value in required_checks)
    aws_ok = checks["aws"] in {"available", "not_configured"}
    mail_services_ok = mail_services_status in {"available", "not_configured"}
    return {
        "status": "ready" if required_checks_ok and aws_ok and mail_services_ok else "degraded",
        "checks": checks,
        "services": mail_services,
    }


def main() -> None:
    configure_logging("mail-health")
    _load_local_env()
    database_url = getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    database_engine = create_engine_from_url(database_url)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health/live":
                status, payload = 200, {"status": "alive"}
            elif self.path == "/health/ready":
                payload = build_health(database_engine)
                status = 200 if payload["status"] == "ready" else 503
            else:
                status, payload = 404, {"error": "not_found"}
            body = json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            logger.info("health request: " + format, *args)

    host = getenv("HEALTH_HOST", "0.0.0.0")
    port = int(getenv("HEALTH_PORT", "8080"))
    logger.info("health server starting: host=%s port=%s", host, port)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
