from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
import json
import logging
from typing import Any, Iterator


_LOG_CONTEXT: ContextVar[dict[str, Any]] = ContextVar("mail_sort_log_context", default={})


@contextmanager
def log_context(**fields: Any) -> Iterator[None]:
    """Attach per-message fields to every log record in this execution scope."""
    values = {**_LOG_CONTEXT.get(), **{key: value for key, value in fields.items() if value is not None}}
    token = _LOG_CONTEXT.set(values)
    try:
        yield
    finally:
        _LOG_CONTEXT.reset(token)


def add_log_context(**fields: Any) -> None:
    """Add fields to the current context until its enclosing scope exits."""
    _LOG_CONTEXT.set(
        {**_LOG_CONTEXT.get(), **{key: value for key, value in fields.items() if value is not None}}
    )


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "service": self._service_name,
            "logger": record.name,
            "message": record.getMessage(),
            **_LOG_CONTEXT.get(),
        }
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, ensure_ascii=False, default=str, separators=(",", ":"))


def configure_logging(service_name: str) -> None:
    console = logging.StreamHandler()
    console.setFormatter(JsonFormatter(service_name))
    logging.basicConfig(level=logging.INFO, handlers=[console], force=True)
