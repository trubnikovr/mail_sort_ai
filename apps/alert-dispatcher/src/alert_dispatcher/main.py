import logging
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from mail_sort_database.models import Alert
from mail_sort_database.session import create_session_factory, session_scope
from mail_sort_logging import configure_logging
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker
from datetime import UTC, datetime, timedelta
from os import environ, getenv
from pathlib import Path


logger = logging.getLogger(__name__)


def load_local_env() -> None:
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


def _prtg_payload(alert: Alert) -> bytes:
    root = ElementTree.Element("prtg")
    result = ElementTree.SubElement(root, "result")
    ElementTree.SubElement(result, "channel").text = "Critical alerts"
    ElementTree.SubElement(result, "value").text = "1"
    ElementTree.SubElement(root, "text").text = (
        f"{alert.title}: {alert.message} (alert_id={alert.id})"
    )[:1024]
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


class AlertDeliveryWorker:
    def __init__(self, sessions: sessionmaker[Session], prtg_push_url: str) -> None:
        self._sessions = sessions
        self._prtg_push_url = prtg_push_url

    def _claim(self) -> Alert | None:
        now = datetime.now(UTC)
        statement = (
            select(Alert)
            .where(
                or_(
                    (Alert.status == "pending") & (Alert.retry_at <= now),
                    (Alert.status == "processing") & (Alert.locked_at < now - timedelta(minutes=2)),
                )
            )
            .order_by(Alert.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        with session_scope(self._sessions) as session:
            alert = session.scalar(statement)
            if alert is None:
                return None
            alert.status = "processing"
            alert.locked_at = now
            alert.attempts += 1
            return alert

    def run_once(self) -> bool:
        alert = self._claim()
        if alert is None:
            return False
        try:
            request = Request(
                self._prtg_push_url,
                data=_prtg_payload(alert),
                headers={"Content-Type": "application/xml", "User-Agent": "mail-sort-alert-dispatcher/0.1"},
                method="POST",
            )
            with urlopen(request, timeout=10) as response:
                response.read(1024)
                if not 200 <= response.status < 300:
                    raise RuntimeError(f"PRTG returned HTTP {response.status}")
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as error:
            delay = min(3600, 15 * (2 ** min(alert.attempts - 1, 8)))
            with session_scope(self._sessions) as session:
                current = session.get(Alert, alert.id, with_for_update=True)
                if current is not None:
                    current.status = "pending"
                    current.locked_at = None
                    current.last_error = type(error).__name__
                    current.retry_at = datetime.now(UTC) + timedelta(seconds=delay)
            logger.error(
                "alert delivery failed: alert_id=%s retry_in_seconds=%s error_type=%s",
                alert.id, delay, type(error).__name__,
            )
            return True

        with session_scope(self._sessions) as session:
            current = session.get(Alert, alert.id, with_for_update=True)
            if current is not None:
                current.status = "delivered"
                current.locked_at = None
                current.last_error = None
                current.delivered_at = datetime.now(UTC)
        logger.warning("critical alert delivered to PRTG: alert_id=%s source=%s", alert.id, alert.source)
        return True

    def run_forever(self, poll_interval_seconds: int) -> None:
        logger.info("alert delivery worker started: provider=prtg")
        while True:
            if not self.run_once():
                sleep(poll_interval_seconds)


def main() -> None:
    configure_logging("alert-dispatcher")
    load_local_env()
    database_url = getenv("DATABASE_URL", "").strip()
    prtg_push_url = getenv("PRTG_PUSH_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL is required")
    if not prtg_push_url:
        logger.warning("PRTG_PUSH_URL is empty; alert delivery is disabled and alerts remain in PostgreSQL")
        while True:
            sleep(60)
    poll_interval = max(1, int(getenv("ALERT_POLL_INTERVAL_SECONDS", "5")))
    worker = AlertDeliveryWorker(create_session_factory(database_url), prtg_push_url)
    worker.run_forever(poll_interval)


if __name__ == "__main__":
    main()
