from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
import atexit
import json
import logging
from logging.handlers import QueueHandler, QueueListener
from os import getenv
from queue import Full, Queue
import sys
from threading import Lock
from typing import Any, Iterator

from sqlalchemy import delete, insert
from sqlalchemy.exc import SQLAlchemyError

from mail_sort_database.models import SystemLog
from mail_sort_database.session import create_engine_from_url


_LOG_CONTEXT: ContextVar[dict[str, Any]] = ContextVar("mail_sort_log_context", default={})
_DB_LOG_LISTENER: QueueListener | None = None
_DB_LOG_LOCK = Lock()


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


class PostgresLogHandler(logging.Handler):
    def __init__(self, service_name: str, database_url: str) -> None:
        super().__init__()
        self._service_name = service_name
        self._engine = create_engine_from_url(database_url)
        self._retention_days = max(1, int(getenv("SYSTEM_LOG_RETENTION_DAYS", "30")))
        self._since_cleanup = 0
        self._last_error_notice = 0.0

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()[:8192]
            exception = self.formatter.formatException(record.exc_info)[:20_000] if record.exc_info else None
            context = json.loads(json.dumps(_LOG_CONTEXT.get(), default=str))
            values = {
                "created_at": datetime.fromtimestamp(record.created, UTC),
                "level": record.levelname[:16],
                "service": self._service_name[:64],
                "logger": record.name[:255],
                "message": message,
                "exception": exception,
                "context": context,
            }
            with self._engine.begin() as connection:
                connection.execute(insert(SystemLog).values(**values))
                self._since_cleanup += 1
                if self._since_cleanup >= 1000:
                    cutoff = datetime.now(UTC) - timedelta(days=self._retention_days)
                    connection.execute(delete(SystemLog).where(SystemLog.created_at < cutoff))
                    self._since_cleanup = 0
        except (SQLAlchemyError, OSError, ValueError, TypeError) as error:
            # The console handler remains the durable fallback if PostgreSQL is unavailable.
            import time
            now = time.monotonic()
            if now - self._last_error_notice >= 60:
                self._last_error_notice = now
                sys.stderr.write(
                    f"mail-sort database log write failed: {type(error).__name__}\n"
                )

    def close(self) -> None:
        self._engine.dispose()
        super().close()


class BoundedQueueHandler(QueueHandler):
    def enqueue(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except Full:
            # Never block mail processing because the database log queue is full.
            pass


def _stop_database_log_listener() -> None:
    global _DB_LOG_LISTENER
    with _DB_LOG_LOCK:
        if _DB_LOG_LISTENER is not None:
            _DB_LOG_LISTENER.stop()
            for handler in _DB_LOG_LISTENER.handlers:
                handler.close()
            _DB_LOG_LISTENER = None


atexit.register(_stop_database_log_listener)


def configure_logging(service_name: str) -> None:
    global _DB_LOG_LISTENER
    _stop_database_log_listener()
    console = logging.StreamHandler()
    console.setFormatter(JsonFormatter(service_name))
    handlers: list[logging.Handler] = [console]
    database_url = getenv("DATABASE_URL", "").strip()
    if database_url:
        database_handler = PostgresLogHandler(service_name, database_url)
        database_handler.setFormatter(JsonFormatter(service_name))
        database_handler.setLevel(getattr(logging, getenv("SYSTEM_LOG_LEVEL", "INFO").upper(), logging.INFO))
        log_queue: Queue[logging.LogRecord] = Queue(maxsize=5000)
        handlers.append(BoundedQueueHandler(log_queue))
        _DB_LOG_LISTENER = QueueListener(log_queue, database_handler, respect_handler_level=True)
        _DB_LOG_LISTENER.start()
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)
