import json
import logging
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from mail_sort_logging import configure_logging

LOGGER = logging.getLogger("mail_sort_runtime")
SERVICES = {
    "mail-collector": "mail_collector.main",
    "mail-decision": "mail_decision.main",
    "mail-router": "mail_router.main",
}
STOP = threading.Event()
LOCK = threading.Lock()


@dataclass
class ManagedProcess:
    name: str
    module: str
    process: subprocess.Popen[bytes] | None = None
    started_at: float = 0
    restart_at: float = 0
    restarts: int = 0
    backoff_seconds: int = 1
    last_exit_code: int | None = None
    state: str = "starting"


PROCESSES = {
    name: ManagedProcess(name, module) for name, module in SERVICES.items()
}


def _start(managed: ManagedProcess) -> None:
    managed.process = subprocess.Popen([sys.executable, "-m", managed.module])
    managed.started_at = time.monotonic()
    managed.state = "running"
    LOGGER.info("service process started: service=%s pid=%s", managed.name, managed.process.pid)


def _monitor(managed: ManagedProcess, now: float) -> None:
    if managed.process is None:
        if now >= managed.restart_at and not STOP.is_set():
            try:
                _start(managed)
            except OSError as error:
                managed.state = "restarting"
                managed.last_exit_code = None
                delay = managed.backoff_seconds
                managed.restart_at = now + delay
                managed.backoff_seconds = min(60, managed.backoff_seconds * 2)
                managed.restarts += 1
                LOGGER.error(
                    "service process could not start: service=%s error_type=%s retry_in_seconds=%s",
                    managed.name, type(error).__name__, delay,
                )
        return

    exit_code = managed.process.poll()
    if exit_code is None:
        if now - managed.started_at >= 60:
            managed.backoff_seconds = 1
        return

    managed.last_exit_code = exit_code
    managed.process = None
    managed.state = "restarting"
    managed.restart_at = now + managed.backoff_seconds
    delay = managed.backoff_seconds
    managed.backoff_seconds = min(60, managed.backoff_seconds * 2)
    managed.restarts += 1
    LOGGER.error(
        "service process exited: service=%s exit_code=%s retry_in_seconds=%s",
        managed.name, exit_code, delay,
    )


def _snapshot() -> dict[str, Any]:
    with LOCK:
        services = {
            name: {
                "status": process.state,
                "pid": process.process.pid if process.process is not None else None,
                "restart_count": process.restarts,
                "last_exit_code": process.last_exit_code,
            }
            for name, process in PROCESSES.items()
        }
    healthy = all(service["status"] == "running" for service in services.values())
    return {"status": "ready" if healthy else "degraded", "services": services}


def _health_server() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/health/services":
                self.send_error(404)
                return
            payload = json.dumps(_snapshot(), separators=(",", ":")).encode()
            self.send_response(200 if json.loads(payload)["status"] == "ready" else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            LOGGER.info("service health request: " + format, *args)

    server = ThreadingHTTPServer(("0.0.0.0", 8081), Handler)
    server.serve_forever()


def _shutdown() -> None:
    STOP.set()
    for managed in PROCESSES.values():
        if managed.process is not None and managed.process.poll() is None:
            managed.process.terminate()
    deadline = time.monotonic() + 10
    for managed in PROCESSES.values():
        process = managed.process
        if process is None:
            continue
        remaining = max(0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main() -> None:
    configure_logging("mail-app")
    signal.signal(signal.SIGTERM, lambda _signum, _frame: STOP.set())
    signal.signal(signal.SIGINT, lambda _signum, _frame: STOP.set())
    threading.Thread(target=_health_server, name="health", daemon=True).start()
    LOGGER.info("mail service supervisor started: services=%s", ",".join(SERVICES))
    try:
        while not STOP.is_set():
            with LOCK:
                now = time.monotonic()
                for managed in PROCESSES.values():
                    _monitor(managed, now)
            STOP.wait(1)
    finally:
        _shutdown()
        LOGGER.info("mail service supervisor stopped")


if __name__ == "__main__":
    main()
